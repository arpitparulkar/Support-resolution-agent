from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupportState(TypedDict, total=False):
    """Conversation and workflow state for the support agent."""

    messages: Annotated[list[AnyMessage], add_messages]
    order_id: str | None
    intent: str | None
    authenticated_user: dict[str, Any] | None
    active_agent: str | None
    refund_request: dict[str, Any] | None
    ticket_id: str | None
    escalated: bool
    approval_status: str | None
    error_count: int
    handoff_count: int
    handoff_requested: bool
    escalation_requested: bool
    escalation_reason: str | None
    tool_error_count: int
    iteration: int
    last_user_message_id: str | None
    refund_confirmed: bool
    refund_confirmed_order_ids: list[str]
    llm_failed: bool
    customer_id: int | None
    conversation_id: int | None
