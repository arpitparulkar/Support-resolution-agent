from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.db.repositories import Repo

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_conversations(current_user: User = Depends(get_current_user), db=Depends(get_db)) -> list[dict]:
    repo = Repo(db)
    conversations = repo.list_conversations(user_id=current_user.id)
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in conversations]


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)) -> dict:
    repo = Repo(db)
    conversation = repo.get_conversation(conversation_id, user_id=current_user.id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {"id": msg.id, "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}
            for msg in sorted(conversation.messages, key=lambda m: m.id)
        ],
    }
