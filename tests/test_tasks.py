# tests/test_tasks.py
# Automated unit & integration tests for authenticated Task API endpoints and tenant isolation.
# Connects to: src/task_api/main.py, src/task_api/database.py, src/task_api/auth.py
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


def get_auth_headers(email: str = "testuser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    """Verify public health check endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unauthenticated_task_access_fails():
    """Verify accessing task endpoints without auth token returns 401 Unauthorized."""
    response = client.get("/tasks")
    assert response.status_code == 401


def test_create_and_get_task_authenticated():
    """Test task creation and retrieval by owner."""
    headers = get_auth_headers("user1@example.com")
    payload = {
        "title": "Design Database Schema",
        "description": "Create ERD diagram",
        "priority": "high",
        "status": "todo"
    }
    create_res = client.post("/tasks", json=payload, headers=headers)
    assert create_res.status_code == 201
    task_data = create_res.json()
    assert task_data["id"] is not None
    assert task_data["title"] == payload["title"]
    assert "owner_id" in task_data

    # Fetch task by ID
    task_id = task_data["id"]
    get_res = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["title"] == payload["title"]


def test_user_tenant_isolation():
    """Verify User A cannot read or mutate User B's tasks."""
    headers_user_a = get_auth_headers("usera@example.com")
    headers_user_b = get_auth_headers("userb@example.com")

    # User A creates a task
    create_res = client.post("/tasks", json={"title": "User A Private Task"}, headers=headers_user_a)
    task_id = create_res.json()["id"]

    # User B tries to get User A's task -> 404 Not Found (tenant isolated)
    get_res_b = client.get(f"/tasks/{task_id}", headers=headers_user_b)
    assert get_res_b.status_code == 404

    # User B tries to update User A's task -> 404 Not Found
    put_res_b = client.put(f"/tasks/{task_id}", json={"title": "Hacked Title"}, headers=headers_user_b)
    assert put_res_b.status_code == 404

    # User B lists tasks -> total 0
    list_res_b = client.get("/tasks", headers=headers_user_b)
    assert list_res_b.json()["total"] == 0


def test_list_and_filter_tasks_authenticated():
    """Test listing tasks with filters for authenticated owner."""
    headers = get_auth_headers("filteruser@example.com")
    client.post("/tasks", json={"title": "Backend Setup", "status": "completed", "priority": "medium"}, headers=headers)
    client.post("/tasks", json={"title": "Frontend UI", "status": "todo", "priority": "high"}, headers=headers)

    res = client.get("/tasks?status=completed", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["tasks"][0]["title"] == "Backend Setup"


def test_update_and_delete_task_authenticated():
    """Test task update and deletion by owner."""
    headers = get_auth_headers("cruduser@example.com")
    create_res = client.post("/tasks", json={"title": "Task to delete"}, headers=headers)
    task_id = create_res.json()["id"]

    update_res = client.put(f"/tasks/{task_id}", json={"title": "Updated Title"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Title"

    del_res = client.delete(f"/tasks/{task_id}", headers=headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_res.status_code == 404
