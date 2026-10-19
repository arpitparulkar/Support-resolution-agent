from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, require_admin
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.db.repositories import Repo
from backend.app.schemas.tickets import TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
def list_tickets(current_user: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    repo = Repo(db)
    tickets = repo.list_tickets()
    return [
        {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "issue": ticket.issue,
            "priority": ticket.priority,
            "status": ticket.status,
            "order_id": ticket.order_id,
            "created_at": ticket.created_at.isoformat(),
        }
        for ticket in tickets
    ]


@router.patch("/{ticket_id}")
def update_ticket(ticket_id: str, payload: TicketUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    repo = Repo(db)
    ticket = repo.update_ticket(ticket_id, status=payload.status, priority=payload.priority)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return {"ticket_id": ticket.ticket_id, "status": ticket.status, "priority": ticket.priority}
