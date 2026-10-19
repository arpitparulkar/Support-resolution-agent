from __future__ import annotations

from pydantic import BaseModel, Field


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None


class TicketRead(BaseModel):
    id: int
    ticket_id: str
    issue: str
    priority: str
    status: str
    order_id: str | None = None
