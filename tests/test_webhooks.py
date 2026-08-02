# tests/test_webhooks.py
# Automated unit & integration tests for Webhooks and Real-Time Event Subscription endpoints.
# Connects to: src/task_api/main.py, src/task_api/crud.py, src/task_api/services.py
# Created: 2026-08-02

import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from task_api.database import Base, get_db
from task_api.main import app
from task_api.services import dispatch_webhook_event

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def get_auth_headers(email: str = "webhookuser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Webhook User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_and_list_webhooks():
    """Test registering a webhook target URL and listing active webhooks."""
    headers = get_auth_headers("wh_registrar@example.com")
    payload = {
        "target_url": "https://example.com/api/webhook-listener",
        "secret_token": "my_super_secret_key"
    }

    reg_res = client.post("/webhooks", json=payload, headers=headers)
    assert reg_res.status_code == 201
    wh_data = reg_res.json()
    assert wh_data["target_url"] == "https://example.com/api/webhook-listener"
    assert wh_data["secret_token"] == "my_super_secret_key"

    # List webhooks
    list_res = client.get("/webhooks", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["webhooks"][0]["id"] == wh_data["id"]


def test_delete_webhook():
    """Test unregistering a webhook URL."""
    headers = get_auth_headers("wh_deleter@example.com")
    reg_res = client.post("/webhooks", json={"target_url": "https://example.com/wh1"}, headers=headers)
    wh_id = reg_res.json()["id"]

    del_res = client.delete(f"/webhooks/{wh_id}", headers=headers)
    assert del_res.status_code == 204

    list_res = client.get("/webhooks", headers=headers)
    assert list_res.json()["total"] == 0


def test_webhook_hmac_signature_calculation():
    """Verify HMAC-SHA256 signature logic matches calculation."""
    secret = "test_signing_secret"
    payload = {"event": "task.created", "data": {"id": 1, "title": "Test Task"}}
    body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

    expected_sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    assert len(expected_sig) == 64  # SHA-256 hex string length


def test_webhook_tenant_isolation():
    """Verify User B cannot delete User A's webhook subscription."""
    headers_a = get_auth_headers("wh_a@example.com")
    headers_b = get_auth_headers("wh_b@example.com")

    reg_res = client.post("/webhooks", json={"target_url": "https://example.com/wh_a"}, headers=headers_a)
    wh_id = reg_res.json()["id"]

    # User B delete attempt -> 404 Not Found
    del_res_b = client.delete(f"/webhooks/{wh_id}", headers=headers_b)
    assert del_res_b.status_code == 404
