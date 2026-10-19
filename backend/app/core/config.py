from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'backend' / 'support_agent.db'}")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", str(BASE_DIR / "backend" / ".chroma"))
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", str(BASE_DIR / "backend" / "support_agent_state.db"))
CORS_ORIGINS: List[str] = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]


def validate_jwt_secret() -> str:
	secret = os.getenv("JWT_SECRET")
	if secret is None or len(secret.encode("utf-8")) < 32:
		raise RuntimeError("JWT_SECRET must be set and contain at least 32 bytes.")
	return secret

