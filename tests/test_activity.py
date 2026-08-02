# tests/test_activity.py
# Automated unit & integration tests for Task Activity Audit Trail logging.
# Connects to: src/task_api/main.py, src/task_api/crud.py
# Created: 2026-08-02

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from task_api.database import Base, get_db
from task_api.main import app

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


def get_auth_headers(email: str = "audituser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Audit User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_creation_activity_log():
    """Verify creating a task generates a 'task.created' audit log."""
    headers = get_auth_headers("audit1@example.com")
    task_res = client.post("/tasks", json={"title": "Audit Task 1"}, headers=headers)
    task_id = task_res.json()["id"]

    act_res = client.get(f"/tasks/{task_id}/activity", headers=headers)
    assert act_res.status_code == 200
    data = act_res.json()
    assert data["total"] == 1
    assert data["activities"][0]["action"] == "task.created"
    assert data["activities"][0]["new_value"] == "Audit Task 1"


def test_task_update_field_diff_activity_log():
    """Verify updating task fields creates detailed field_changed, old_value, and new_value audit entries."""
    headers = get_auth_headers("audit2@example.com")
    task_res = client.post("/tasks", json={"title": "Initial Title", "status": "todo"}, headers=headers)
    task_id = task_res.json()["id"]

    # Update status and title
    client.put(f"/tasks/{task_id}", json={"title": "Updated Title", "status": "in_progress"}, headers=headers)

    act_res = client.get(f"/tasks/{task_id}/activity", headers=headers)
    assert act_res.status_code == 200
    logs = act_res.json()["activities"]
    assert len(logs) == 3  # 1 created + 2 updated field diffs

    actions = [log["action"] for log in logs]
    fields = [log["field_changed"] for log in logs if log["field_changed"]]
    assert "task.created" in actions
    assert "title" in fields
    assert "status" in fields


def test_tag_and_attachment_activity_logs():
    """Verify linking tags and uploading attachments create corresponding activity audit entries."""
    headers = get_auth_headers("audit3@example.com")

    task_res = client.post("/tasks", json={"title": "Complex Audit Task"}, headers=headers)
    task_id = task_res.json()["id"]

    tag_res = client.post("/tags", json={"name": "DevOps"}, headers=headers)
    tag_id = tag_res.json()["id"]

    # Attach tag
    client.post(f"/tasks/{task_id}/tags/{tag_id}", headers=headers)

    # Upload attachment
    files = {"file": ("log.txt", io.BytesIO(b"Log file data"), "text/plain")}
    client.post(f"/tasks/{task_id}/attachments", files=files, headers=headers)

    act_res = client.get(f"/tasks/{task_id}/activity", headers=headers)
    assert act_res.status_code == 200
    actions = [log["action"] for log in act_res.json()["activities"]]
    assert "tag.attached" in actions
    assert "attachment.uploaded" in actions


def test_user_overall_activity_audit_trail():
    """Verify /activity endpoint returns overall audit entries across all tasks for the user."""
    headers = get_auth_headers("audit_user_overall@example.com")
    client.post("/tasks", json={"title": "Task A"}, headers=headers)
    client.post("/tasks", json={"title": "Task B"}, headers=headers)

    overall_res = client.get("/activity", headers=headers)
    assert overall_res.status_code == 200
    assert overall_res.json()["total"] == 2


def test_activity_tenant_isolation():
    """Verify User B cannot view User A's task activity logs."""
    headers_a = get_auth_headers("audit_a@example.com")
    headers_b = get_auth_headers("audit_b@example.com")

    task_a = client.post("/tasks", json={"title": "User A Private Task"}, headers=headers_a).json()

    act_res_b = client.get(f"/tasks/{task_a['id']}/activity", headers=headers_b)
    assert act_res_b.status_code == 404
