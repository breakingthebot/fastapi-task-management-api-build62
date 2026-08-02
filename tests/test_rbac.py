# tests/test_rbac.py
# Automated unit & integration tests for Workspaces and RBAC Permission Enforcement.
# Connects to: src/task_api/main.py, src/task_api/crud.py
# Created: 2026-08-02

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


def create_user_headers(email: str, password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": f"User {email}"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_workspace():
    """Verify creating a team workspace automatically grants ADMIN role to creator."""
    headers_owner = create_user_headers("ws_owner@example.com")
    ws_res = client.post("/workspaces", json={"name": "Dev Team", "description": "Backend Workspace"}, headers=headers_owner)
    assert ws_res.status_code == 201
    ws_data = ws_res.json()
    assert ws_data["name"] == "Dev Team"
    assert len(ws_data["members"]) == 1
    assert ws_data["members"][0]["role"] == "admin"

    list_res = client.get("/workspaces", headers=headers_owner)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1


def test_add_member_and_rbac_permissions():
    """Verify Admin can add Editor and Viewer, Editor can create/update tasks, and Viewer is restricted."""
    headers_admin = create_user_headers("admin@example.com")
    headers_editor = create_user_headers("editor@example.com")
    headers_viewer = create_user_headers("viewer@example.com")

    # Admin creates workspace
    ws_id = client.post("/workspaces", json={"name": "Engineering Workspace"}, headers=headers_admin).json()["id"]

    # Admin adds Editor and Viewer
    client.post(f"/workspaces/{ws_id}/members", json={"user_email": "editor@example.com", "role": "editor"}, headers=headers_admin)
    client.post(f"/workspaces/{ws_id}/members", json={"user_email": "viewer@example.com", "role": "viewer"}, headers=headers_admin)

    # Non-admin cannot add members -> 403 Forbidden
    forbidden_add = client.post(f"/workspaces/{ws_id}/members", json={"user_email": "other@example.com", "role": "editor"}, headers=headers_editor)
    assert forbidden_add.status_code == 403

    # Admin creates workspace task
    task_res = client.post("/tasks", json={"title": "Admin Task", "workspace_id": ws_id}, headers=headers_admin)
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # Viewer can read workspace task
    read_res = client.get(f"/tasks/{task_id}", headers=headers_viewer)
    assert read_res.status_code == 200
    assert read_res.json()["title"] == "Admin Task"

    # Viewer cannot update workspace task -> 403 Forbidden
    update_res_viewer = client.put(f"/tasks/{task_id}", json={"title": "Viewer Edit Attempt"}, headers=headers_viewer)
    assert update_res_viewer.status_code == 403

    # Editor updates workspace task
    update_res_editor = client.put(f"/tasks/{task_id}", json={"title": "Valid Editor Update"}, headers=headers_editor)
    assert update_res_editor.status_code == 200

    # Non-owner Editor cannot delete Admin's workspace task -> 403 Forbidden
    del_res_editor = client.delete(f"/tasks/{task_id}", headers=headers_editor)
    assert del_res_editor.status_code == 403

    # Admin can delete workspace task -> 204 No Content
    del_res_admin = client.delete(f"/tasks/{task_id}", headers=headers_admin)
    assert del_res_admin.status_code == 204
