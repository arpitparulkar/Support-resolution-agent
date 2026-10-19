from __future__ import annotations

import os
import secrets

os.environ["DATABASE_URL"] = "sqlite:///./backend/test_support_agent.db"
os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
os.environ["RAG_EMBEDDINGS_ENABLED"] = "false"