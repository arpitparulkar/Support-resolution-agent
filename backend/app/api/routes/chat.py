from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.db.repositories import Repo
from backend.app.schemas.chat import ChatRequest

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(
    payload: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:

    repo = Repo(db)
    conversation = None

    # Find an existing conversation or create a new one.
    if payload.conversation_id is not None:
        conversation = repo.get_conversation(
            payload.conversation_id,
            user_id=current_user.id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
    else:
        conversation = repo.create_conversation(
            current_user.id,
            title="New chat",
        )

    # Save the user's message.
    repo.add_message(
        conversation.id,
        "user",
        payload.message,
    )

    # Check whether the Groq API key is configured.
    if not os.getenv("GROQ_API_KEY"):
        reply = (
            "I can answer that once the Groq API key is configured. "
            "The support system is ready, but the LLM is unavailable right now."
        )

    else:
        graph = request.app.state.agent_graph

        # Run the LangGraph workflow.
        state = graph.invoke(
            {
                "messages": [
                    HumanMessage(content=payload.message)
                ],
                "authenticated_user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "full_name": current_user.full_name,
                    "role": current_user.role,
                },
                "customer_id": current_user.id,
                "conversation_id": conversation.id,
            },
            config={
                "configurable": {
                    "thread_id": f"conv-{conversation.id}",
                },
                "recursion_limit": 30,
            },
        )

        messages = state.get("messages", [])

        # ==========================================
        # LANGGRAPH DEBUGGING
        # ==========================================

        print(
            "\n========== LANGGRAPH DEBUG ==========",
            flush=True,
        )

        for i, message in enumerate(messages):
            print(
                f"Message {i}: "
                f"type={getattr(message, 'type', 'unknown')} | "
                f"content={str(getattr(message, 'content', ''))[:300]} | "
                f"tool_calls={getattr(message, 'tool_calls', [])}",
                flush=True,
            )

        print(
            "Agent state:",
            {
                "active_agent": state.get("active_agent"),
                "escalated": state.get("escalated"),
                "ticket_id": state.get("ticket_id"),
                "llm_failed": state.get("llm_failed"),
            },
            flush=True,
        )

        print(
            "=====================================\n",
            flush=True,
        )

        # ==========================================
        # EXTRACT FINAL AI RESPONSE
        # ==========================================

        reply = next(
            (
                message.content
                for message in reversed(messages)
                if getattr(message, "type", "") == "ai"
                and isinstance(message.content, str)
                and message.content.strip()
                and not getattr(message, "tool_calls", None)
            ),
            None,
        )

        # Handle workflows without a final AI message.
        if reply is None:
            ticket_id = state.get("ticket_id")

            if state.get("escalated") and ticket_id:
                reply = (
                    "I couldn't resolve your request automatically, "
                    "so I've created a support ticket for human review. "
                    f"Your ticket ID is {ticket_id}. "
                    "Our support team can investigate further."
                )
            else:
                reply = (
                    "I'm unable to complete your request right now. "
                    "Please try again or contact support."
                )

    # Save the assistant's response.
    repo.add_message(
        conversation.id,
        "assistant",
        reply,
    )

    return {
        "conversation_id": conversation.id,
        "reply": reply,
    }


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:

    repo = Repo(db)
    conversation = None

    if payload.conversation_id is not None:
        conversation = repo.get_conversation(
            payload.conversation_id,
            user_id=current_user.id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
    else:
        conversation = repo.create_conversation(
            current_user.id,
            title="New chat",
        )

    # Streaming is not implemented yet.
    content = (
        "This is a streaming placeholder response from the "
        "support agent. Connect the Groq model to stream live tokens."
    )

    async def event_stream() -> Any:
        for word in content.split():
            yield (
                f"data: {json.dumps({'content': word + ' '})}\n\n"
            )

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )