# tests/test_tasks.py
# Automated unit & integration tests for Task API endpoints.
# Connects to: src/task_api/main.py, src/task_api/database.py
# Created: 2026-08-02

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from task_api.database import Base, get_db
from task_api.main import app

# Setup in-memory SQLite database using StaticPool to maintain a single connection across threads
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


def test_health_check():
    """Verify health check endpoint returns 200 OK and valid status metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Task Management API"
    assert "version" in data


def test_version_endpoint():
    """Verify version endpoint returns product version."""
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()


def test_create_and_get_task():
    """Test task creation and retrieval by ID."""
    payload = {
        "title": "Design Database Schema",
        "description": "Create ERD diagram and define initial migration scripts",
        "priority": "high",
        "status": "todo"
    }
    create_res = client.post("/tasks", json=payload)
    assert create_res.status_code == 201
    task_data = create_res.json()
    assert task_data["id"] is not None
    assert task_data["title"] == payload["title"]
    assert task_data["priority"] == "high"

    # Fetch task by ID
    task_id = task_data["id"]
    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == payload["title"]


def test_list_and_filter_tasks():
    """Test listing tasks with status, priority, and search filtering."""
    client.post("/tasks", json={"title": "Backend Setup", "status": "completed", "priority": "medium"})
    client.post("/tasks", json={"title": "Frontend UI", "status": "todo", "priority": "high"})
    client.post("/tasks", json={"title": "Deploy Server", "status": "todo", "priority": "medium"})

    # List all
    res = client.get("/tasks")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["tasks"]) == 3

    # Filter by status
    res_status = client.get("/tasks?status=completed")
    assert res_status.json()["total"] == 1
    assert res_status.json()["tasks"][0]["title"] == "Backend Setup"

    # Filter by priority
    res_priority = client.get("/tasks?priority=high")
    assert res_priority.json()["total"] == 1
    assert res_priority.json()["tasks"][0]["title"] == "Frontend UI"

    # Search keyword
    res_search = client.get("/tasks?search=Deploy")
    assert res_search.json()["total"] == 1
    assert res_search.json()["tasks"][0]["title"] == "Deploy Server"


def test_update_task():
    """Test partial update of a task's status and title."""
    create_res = client.post("/tasks", json={"title": "Initial Task", "status": "todo"})
    task_id = create_res.json()["id"]

    update_payload = {"title": "Updated Task Title", "status": "in_progress"}
    update_res = client.put(f"/tasks/{task_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["title"] == "Updated Task Title"
    assert updated_data["status"] == "in_progress"


def test_delete_task():
    """Test task deletion and verification of 404 on subsequent read."""
    create_res = client.post("/tasks", json={"title": "Task to delete"})
    task_id = create_res.json()["id"]

    del_res = client.delete(f"/tasks/{task_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/tasks/{task_id}")
    assert get_res.status_code == 404


def test_get_nonexistent_task_returns_404():
    """Verify requesting a non-existent ID returns 404 Not Found."""
    res = client.get("/tasks/99999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]
