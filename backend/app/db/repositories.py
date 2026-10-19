from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Conversation, Message, Order, Ticket, ToolCallLog, User


class Repo:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create_user(self, *, email: str, full_name: str, password_hash: str, role: str = "customer") -> User:
        user = User(email=email, full_name=full_name, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_order_by_id(self, order_id: str) -> Order | None:
        return self.db.scalar(select(Order).where(Order.order_id == order_id))

    def get_orders_for_user(self, user_email: str) -> list[Order]:
        return self.db.scalars(select(Order).where(Order.customer_name == user_email)).all()

    def create_ticket(self, *, issue: str, priority: str, order_id: str | None, customer_user_id: int | None, conversation_id: int | None = None) -> Ticket:
        base = self.db.scalar(select(Ticket).order_by(Ticket.id.desc())) or None
        next_number = (base.id if base else 99) + 1 if base else 101
        ticket = Ticket(
            ticket_id=f"TKT{next_number}",
            issue=issue,
            priority=priority,
            status="open",
            order_id=order_id,
            customer_user_id=customer_user_id,
            conversation_id=conversation_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def list_tickets(self) -> list[Ticket]:
        return self.db.scalars(select(Ticket).order_by(Ticket.created_at.desc())).all()

    def update_ticket(self, ticket_id: str, *, status: str | None = None, priority: str | None = None) -> Ticket | None:
        ticket = self.db.scalar(select(Ticket).where(Ticket.ticket_id == ticket_id))
        if not ticket:
            return None
        if status is not None:
            ticket.status = status
        if priority is not None:
            ticket.priority = priority
        ticket.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def create_conversation(self, user_id: int, title: str = "New chat") -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_conversation(self, conversation_id: int, user_id: int | None = None) -> Conversation | None:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if user_id is not None:
            stmt = stmt.where(Conversation.user_id == user_id)
        return self.db.scalar(stmt)

    def list_conversations(self, user_id: int | None = None) -> list[Conversation]:
        stmt = select(Conversation).order_by(Conversation.updated_at.desc())
        if user_id is not None:
            stmt = stmt.where(Conversation.user_id == user_id)
        return self.db.scalars(stmt).all()

    def log_tool_call(self, *, conversation_id: int | None, tool_name: str, args: dict[str, Any], result: dict[str, Any], latency_ms: int) -> ToolCallLog:
        record = ToolCallLog(
            conversation_id=conversation_id,
            tool_name=tool_name,
            args=str(args),
            result=str(result),
            latency_ms=latency_ms,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_tool_logs(self, conversation_id: int | None = None) -> list[ToolCallLog]:
        stmt = select(ToolCallLog).order_by(ToolCallLog.created_at.desc())
        if conversation_id is not None:
            stmt = stmt.where(ToolCallLog.conversation_id == conversation_id)
        return self.db.scalars(stmt).all()
