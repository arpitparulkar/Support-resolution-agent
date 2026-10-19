from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.db.database import engine, init_db
from backend.app.db.models import Base
from backend.app.db.seed import seed
from backend.app.main import app
from backend.app.agent.tools import request_refund



@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed()


def test_auth_register_and_login(client: TestClient) -> None:
    reset_db()
    response = client.post("/auth/register", json={"email": "new.user@example.com", "full_name": "New User", "password": "secret123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token

    login = client.post("/auth/login", json={"email": "new.user@example.com", "password": "secret123"})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_customer_cannot_access_other_customer_conversation(client: TestClient) -> None:
    reset_db()
    first = client.post("/auth/register", json={"email": "alpha@example.com", "full_name": "Alpha", "password": "secret123"})
    second = client.post("/auth/register", json={"email": "beta@example.com", "full_name": "Beta", "password": "secret123"})
    alpha_token = first.json()["access_token"]
    beta_token = second.json()["access_token"]
    alpha_headers = {"Authorization": f"Bearer {alpha_token}"}
    beta_headers = {"Authorization": f"Bearer {beta_token}"}

    create = client.post("/chat", json={"message": "Hi"}, headers=alpha_headers)
    conversation_id = create.json()["conversation_id"]
    response = client.get(f"/conversations/{conversation_id}", headers=beta_headers)
    assert response.status_code == 404


def test_rag_tool_returns_chunks_with_sources(client: TestClient) -> None:
    assert app.state.agent_graph is not None
    result = app.state.knowledge_base.search("refund policy", k=2)
    assert result["ok"] is True
    assert len(result["results"]) >= 1
    assert "source" in result["results"][0]


def test_ticket_listing_admin_only(client: TestClient) -> None:
    reset_db()
    admin = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    response = client.get("/tickets", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_registration_cannot_assign_admin_role(client: TestClient) -> None:
    register = client.post("/auth/register", json={"email": "new.admin@example.com", "full_name": "New Admin", "password": "secret123", "role": "admin"})
    assert register.status_code == 422


def test_refund_guardrail_never_claims_success_without_tool(client: TestClient) -> None:
    reset_db()
    result = request_refund.invoke({"order_id": "ORD128", "reason": "damaged chair"})
    assert result["ok"] is False or result.get("eligible") is False


@pytest.mark.parametrize("secret", [None, "too-short"])
def test_startup_requires_strong_jwt_secret(monkeypatch: pytest.MonkeyPatch, secret: str | None) -> None:
    if secret is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set and contain at least 32 bytes"):
        with TestClient(app):
            pass
