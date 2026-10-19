"""Deterministic tests for support tools and graph guardrails."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.graph import build_graph
from agent.tools import (
    check_refund_eligibility,
    create_support_ticket,
    get_order_status,
    request_refund,
)


@pytest.fixture
def data_dir(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Give each test isolated JSON files and a predictable set of orders."""
    delivered_recently = (date.today() - timedelta(days=5)).isoformat()
    delivered_old = (date.today() - timedelta(days=45)).isoformat()
    orders = [
        {
            "order_id": "ORD123",
            "customer": "Rahul",
            "product": "Headphones",
            "status": "Shipped",
            "order_date": date.today().isoformat(),
            "expected_delivery": (date.today() + timedelta(days=4)).isoformat(),
            "delivered_date": None,
            "amount": 89.99,
            "refund_status": "Not requested",
        },
        {
            "order_id": "ORD124",
            "customer": "Priya",
            "product": "Keyboard",
            "status": "Delivered",
            "order_date": delivered_recently,
            "expected_delivery": delivered_recently,
            "delivered_date": delivered_recently,
            "amount": 129.99,
            "refund_status": "Not requested",
        },
        {
            "order_id": "ORD125",
            "customer": "Aisha",
            "product": "Mouse",
            "status": "Delivered",
            "order_date": delivered_recently,
            "expected_delivery": delivered_recently,
            "delivered_date": delivered_recently,
            "amount": 34.50,
            "refund_status": "Refunded",
        },
        {
            "order_id": "ORD128",
            "customer": "Omar",
            "product": "Chair",
            "status": "Delivered",
            "order_date": delivered_old,
            "expected_delivery": delivered_old,
            "delivered_date": delivered_old,
            "amount": 219.00,
            "refund_status": "Not requested",
        },
    ]
    (tmp_path / "orders.json").write_text(json.dumps(orders), encoding="utf-8")
    (tmp_path / "tickets.json").write_text("[]", encoding="utf-8")
    (tmp_path / "policies.txt").write_text(
        "REFUNDS\nRefunds are allowed within 30 days for damaged items.\n", encoding="utf-8"
    )
    monkeypatch.setenv("SUPPORT_AGENT_DATA_DIR", str(tmp_path))
    return tmp_path


class FakeToolCallingModel:
    """A tiny predictable model double for graph tests; it never calls an API."""

    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = list(responses)

    def bind_tools(self, _tools: list[Any]) -> "FakeToolCallingModel":
        return self

    def invoke(self, _messages: list[Any]) -> AIMessage:
        if not self.responses:
            return AIMessage(content="I can help with that.")
        return self.responses.pop(0)


def test_get_order_status_found_and_not_found(data_dir: Any) -> None:
    found = get_order_status.invoke({"order_id": "ORD123"})
    missing = get_order_status.invoke({"order_id": "ORD999"})

    assert found["ok"] is True
    assert found["order"]["status"] == "Shipped"
    assert "customer" not in found["order"]
    assert missing["ok"] is False
    assert missing["error"]["code"] == "order_not_found"


def test_refund_eligibility_and_rejection_cases(data_dir: Any) -> None:
    eligible = check_refund_eligibility.invoke(
        {"order_id": "ORD124", "reason": "damaged keyboard", "customer_name": "Priya"}
    )
    expired = check_refund_eligibility.invoke(
        {"order_id": "ORD128", "reason": "defective chair", "customer_name": "Omar"}
    )
    already_refunded = check_refund_eligibility.invoke(
        {"order_id": "ORD125", "reason": "damaged mouse", "customer_name": "Aisha"}
    )
    wrong_customer = check_refund_eligibility.invoke(
        {"order_id": "ORD124", "reason": "damaged keyboard", "customer_name": "Rahul"}
    )

    assert eligible["eligible"] is True
    assert expired["eligible"] is False
    assert already_refunded["eligible"] is False
    assert wrong_customer["ok"] is False
    assert wrong_customer["error"]["code"] == "verification_failed"


def test_request_refund_records_success_only_after_eligibility(data_dir: Any) -> None:
    result = request_refund.invoke(
        {"order_id": "ORD124", "reason": "damaged keyboard", "customer_name": "Priya"}
    )
    orders = json.loads((data_dir / "orders.json").read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["confirmation_id"].startswith("RFND-")
    assert next(order for order in orders if order["order_id"] == "ORD124")["refund_status"] == "Refunded"


def test_ticket_creation_increments_ids_and_persists(data_dir: Any) -> None:
    first = create_support_ticket.invoke({"issue": "Delivery delay", "priority": "medium", "order_id": "ORD123"})
    second = create_support_ticket.invoke({"issue": "Duplicate charge", "priority": "high"})
    tickets = json.loads((data_dir / "tickets.json").read_text(encoding="utf-8"))

    assert first["ticket_id"] == "TKT101"
    assert second["ticket_id"] == "TKT102"
    assert len(tickets) == 2
    assert tickets[1]["priority"] == "high"


def test_agent_calls_order_status_tool(data_dir: Any) -> None:
    model = FakeToolCallingModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_order_status", "args": {"order_id": "ORD123"}, "id": "call-order"}
                ],
            ),
            AIMessage(content="Your headphones are shipped and expected soon."),
        ]
    )
    agent = build_graph(llm=model)
    state = agent.invoke(
        {"messages": [HumanMessage(content="Can you check order ORD123?")]},
        config={"configurable": {"thread_id": "order-test"}, "recursion_limit": 30},
    )

    assert any(isinstance(message, ToolMessage) and message.name == "get_order_status" for message in state["messages"])
    assert state["order_id"] == "ORD123"


def test_agent_blocks_refund_claim_without_tool_success(data_dir: Any) -> None:
    model = FakeToolCallingModel([AIMessage(content="Your refund has been completed.")])
    agent = build_graph(llm=model)
    state = agent.invoke(
        {"messages": [HumanMessage(content="My keyboard is damaged.")]},
        config={"configurable": {"thread_id": "refund-guard-test"}, "recursion_limit": 30},
    )

    assert "not completed a refund" in state["messages"][-1].content
    assert state.get("refund_confirmed", False) is False


def test_agent_escalation_creates_high_priority_ticket(data_dir: Any) -> None:
    model = FakeToolCallingModel([AIMessage(content="I will check that for you.")])
    agent = build_graph(llm=model)
    state = agent.invoke(
        {"messages": [HumanMessage(content="My account was charged twice, and nobody is helping me.")]},
        config={"configurable": {"thread_id": "escalation-test"}, "recursion_limit": 30},
    )
    tickets = json.loads((data_dir / "tickets.json").read_text(encoding="utf-8"))

    assert state["escalated"] is True
    assert state["ticket_id"] == "TKT101"
    assert "TKT101" in state["messages"][-1].content
    assert tickets[0]["priority"] == "high"


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="requires a Groq API key")
def test_groq_agent_smoke(data_dir: Any) -> None:
    """Optional live integration check; deterministic behavior is tested above."""
    agent = build_graph()
    state = agent.invoke(
        {"messages": [HumanMessage(content="Hello, please greet me briefly.")]},
        config={"configurable": {"thread_id": "groq-smoke-test"}, "recursion_limit": 30},
    )
    assert isinstance(state["messages"][-1], AIMessage)
