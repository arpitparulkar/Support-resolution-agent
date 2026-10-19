from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.conversations import router as conversation_router
from backend.app.api.routes.tickets import router as ticket_router
from backend.app.agent.multi_agent import build_graph
from backend.app.core.config import CHECKPOINT_DB_PATH, CORS_ORIGINS, validate_jwt_secret
from backend.app.db.database import engine, init_db
from backend.app.db.seed import seed
from backend.app.rag.knowledge_base import KnowledgeBase, ingest_default_knowledge


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    checkpointer_context = None
    try:
        validate_jwt_secret()
        init_db()
        seed()

        knowledge_base = KnowledgeBase(enable_embeddings=os.getenv("RAG_EMBEDDINGS_ENABLED", "true").casefold() == "true")
        ingest_default_knowledge(knowledge_base)
        checkpoint_path = Path(CHECKPOINT_DB_PATH)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpointer_context = SqliteSaver.from_conn_string(str(checkpoint_path))
        checkpointer = checkpointer_context.__enter__()

        app.state.knowledge_base = knowledge_base
        app.state.checkpointer = checkpointer
        app.state.agent_graph = build_graph(knowledge_base=knowledge_base, checkpointer=checkpointer)
        yield
    finally:
        if checkpointer_context is not None:
            checkpointer_context.__exit__(None, None, None)
        engine.dispose()


app = FastAPI(title="Support Resolution AI Agent", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(ticket_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
