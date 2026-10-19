"""Typed conversation state shared by the LangGraph nodes."""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupportState(TypedDict, total=False):
    """Conversation memory and workflow metadata for one support thread."""

    messages: Annotated[list[AnyMessage], add_messages]
    order_id: str | None
    intent: str | None
    ticket_id: str | None
    escalated: bool
    escalation_requested: bool
    escalation_reason: str | None
    tool_error_count: int
    iteration: int
    last_user_message_id: str | None
    refund_confirmed: bool
    refund_confirmed_order_ids: list[str]
    llm_failed: bool
