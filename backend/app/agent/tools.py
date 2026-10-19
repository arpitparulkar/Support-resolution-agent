from __future__ import annotations

import json
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from backend.app.db.database import SessionLocal
from backend.app.db.repositories import Repo
from backend.app.rag.knowledge_base import KnowledgeBase

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ORDER_ID_PATTERN = re.compile(r"^ORD\d{3,}$", re.IGNORECASE)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _get_order(order_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(order_id, str) or not _ORDER_ID_PATTERN.fullmatch(order_id.strip()):
        return None, _error("invalid_order_id", "Provide a valid order ID such as ORD123.")
    db = SessionLocal()
    try:
        repo = Repo(db)
        order = repo.get_order_by_id(order_id.strip().upper())
        if order is None:
            return None, _error("order_not_found", f"No order was found for {order_id.strip().upper()}.")
        return {
            "order_id": order.order_id,
            "customer": order.customer_name,
            "product": order.product,
            "status": order.status,
            "order_date": order.order_date,
            "expected_delivery": order.expected_delivery,
            "delivered_date": order.delivered_date,
            "amount": order.amount,
            "refund_status": order.refund_status,
        }, None
    finally:
        db.close()


@tool
def get_order_status(order_id: str) -> dict[str, Any]:
    """Return the current shipping state for a customer order."""
    order, failure = _get_order(order_id)
    if failure:
        return failure
    assert order is not None
    return {"ok": True, "order": order}


@tool
def lookup_policy(topic: str) -> dict[str, Any]:
    """Read the matching customer support policy section."""
    if not isinstance(topic, str) or not topic.strip():
        return _error("invalid_topic", "Provide a policy topic to look up.")
    policies_path = _PROJECT_ROOT / "data" / "policies.txt"
    if not policies_path.exists():
        return _error("data_file_missing", "The policy file is unavailable.")
    text = policies_path.read_text(encoding="utf-8")
    lowered = topic.casefold()
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        heading = line.strip()
        if heading and heading.isupper():
            current = heading
            sections[current] = []
        elif current:
            sections[current].append(line)
    selected = "GENERAL"
    aliases = {
        "REFUNDS": {"refund", "refunded", "damaged", "defective"},
        "CANCELLATIONS": {"cancel", "cancellation", "cancelled"},
        "DELIVERY": {"delivery", "delayed", "shipping", "arrive"},
        "PAYMENTS": {"payment", "charged", "duplicate", "billing"},
    }
    topic_words = set(re.findall(r"[a-z]+", lowered))
    for name, words in aliases.items():
        if topic_words & words:
            selected = name
            break
    policy = "\n".join(sections.get(selected, [])).strip()
    if not policy:
        return _error("policy_not_found", "No matching policy section is available.")
    return {"ok": True, "topic": selected.casefold(), "policy": policy}


@tool
def check_refund_eligibility(order_id: str, reason: str) -> dict[str, Any]:
    """Apply the simulated damaged-item refund policy to an order."""
    if not isinstance(reason, str) or not reason.strip():
        return _error("invalid_reason", "A refund reason is required.")
    order, failure = _get_order(order_id)
    if failure:
        return failure
    assert order is not None

    if order["refund_status"].casefold() == "refunded":
        return {"ok": True, "eligible": False, "reason": "This order has already been refunded."}
    if order["status"].casefold() != "delivered":
        return {"ok": True, "eligible": False, "reason": "A refund policy applies only to delivered items."}
    normalized_reason = reason.casefold()
    if not any(term in normalized_reason for term in ("damaged", "damage", "defective", "defect")):
        return {"ok": True, "eligible": False, "reason": "This policy covers damaged or defective items only."}
    delivered_value = order.get("delivered_date")
    try:
        days_since_delivery = (date.today() - date.fromisoformat(str(delivered_value))).days
    except (TypeError, ValueError):
        return _error("invalid_order_data", "The delivery date is missing or invalid.")
    if days_since_delivery < 0 or days_since_delivery > 30:
        return {"ok": True, "eligible": False, "reason": "The 30-day return window has expired or the delivery date is in the future."}
    return {"ok": True, "eligible": True, "reason": "The item is within the 30-day damaged-item policy."}


@tool
def request_refund(order_id: str, reason: str, customer_id: int | None = None) -> dict[str, Any]:
    """Record a simulated refund only after the order is eligible."""
    if not isinstance(reason, str) or not reason.strip():
        return _error("invalid_reason", "A refund reason is required.")

    db = SessionLocal()
    try:
        repo = Repo(db)
        order_record = repo.get_order_by_id(order_id.strip().upper())
        if order_record is None:
            return _error("order_not_found", f"No order was found for {order_id.strip().upper()}.")
        if customer_id is not None:
            user = repo.get_user_by_id(customer_id)
            owns_order = user is not None and (
                order_record.user_id == user.id
                or order_record.customer_name.casefold() == user.full_name.casefold()
            )
            if not owns_order:
                return _error("not_authorized", "You can only request a refund for your own order.")
        eligibility = check_refund_eligibility.invoke({"order_id": order_id, "reason": reason})
        if not eligibility.get("ok") or not eligibility.get("eligible"):
            return eligibility
        order_record.refund_status = "Refunded"
        db.commit()
        return {
            "ok": True,
            "confirmation_id": f"RFND-{uuid.uuid4().hex[:10].upper()}",
            "status": "Refunded",
            "message": "The simulated refund was successfully recorded.",
        }
    finally:
        db.close()


@tool
def create_support_ticket(issue: str, priority: str, order_id: str | None = None, customer_id: int | None = None) -> dict[str, Any]:
    """Persist a support ticket and return the generated ticket ID."""
    if not isinstance(issue, str) or not issue.strip():
        return _error("invalid_issue", "Describe the issue before creating a ticket.")
    if not isinstance(priority, str) or priority.casefold() not in {"low", "medium", "high"}:
        return _error("invalid_priority", "Priority must be low, medium, or high.")

    db = SessionLocal()
    try:
        repo = Repo(db)
        ticket = repo.create_ticket(
            issue=issue.strip(),
            priority=priority.casefold(),
            order_id=order_id.strip().upper() if order_id else None,
            customer_user_id=customer_id,
        )
        return {"ok": True, "ticket_id": ticket.ticket_id, "ticket": {"id": ticket.id, "priority": ticket.priority, "status": ticket.status}}
    finally:
        db.close()


SUPPORT_TOOLS = [
    get_order_status,
    lookup_policy,
    check_refund_eligibility,
    request_refund,
    create_support_ticket,
]


def build_support_tools(knowledge_base: KnowledgeBase) -> list[Any]:
    @tool
    def search_knowledge_base(query: str, k: int = 3) -> dict[str, Any]:
        """Search the local company policy and FAQ knowledge base by similarity."""
        return knowledge_base.search(query, k=k)

    return [*SUPPORT_TOOLS, search_knowledge_base]


def build_specialist_tools(knowledge_base: KnowledgeBase) -> dict[str, list[Any]]:
    """Keep each specialist's capabilities narrow and explicit."""
    all_tools = {support_tool.name: support_tool for support_tool in build_support_tools(knowledge_base)}
    return {
        "orders_agent": [all_tools[name] for name in ("get_order_status", "lookup_policy", "search_knowledge_base")],
        "refunds_agent": [all_tools[name] for name in ("check_refund_eligibility", "request_refund", "search_knowledge_base")],
        "escalation_agent": [all_tools[name] for name in ("create_support_ticket", "get_order_status")],
        "single_agent": list(all_tools.values()),
    }
