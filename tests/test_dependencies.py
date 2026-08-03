# tests/test_dependencies.py
# Automated unit & integration tests for Task Dependencies & Subtask Relationships.
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


def test_create_and_list_subtasks():
    """Verify creating a subtask linked to a parent task and retrieving subtasks via GET /tasks/{id}/subtasks."""
    headers = create_user_headers("subtaskuser@example.com")

    # Create parent task
    parent_res = client.post("/tasks", json={"title": "Parent Project Task"}, headers=headers)
    parent_id = parent_res.json()["id"]

    # Create subtask
    subtask_res = client.post("/tasks", json={"title": "Subtask Module 1", "parent_id": parent_id}, headers=headers)
    assert subtask_res.status_code == 201
    subtask_id = subtask_res.json()["id"]
    assert subtask_res.json()["parent_id"] == parent_id

    # List subtasks for parent
    list_res = client.get(f"/tasks/{parent_id}/subtasks", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["tasks"][0]["id"] == subtask_id


def test_self_parent_and_invalid_parent_prevention():
    """Verify a task cannot be set as its own parent or link to a non-existent parent ID."""
    headers = create_user_headers("invalidparent@example.com")

    # Invalid parent ID fails
    res1 = client.post("/tasks", json={"title": "Bad Subtask", "parent_id": 9999}, headers=headers)
    assert res1.status_code == 400

    # Create task
    t_res = client.post("/tasks", json={"title": "Task A"}, headers=headers)
    t_id = t_res.json()["id"]

    # Setting self as parent fails
    res2 = client.put(f"/tasks/{t_id}", json={"parent_id": t_id}, headers=headers)
    assert res2.status_code == 400


def test_parent_task_completion_blocked_by_incomplete_subtasks():
    """Verify completing a parent task fails with HTTP 400 if incomplete subtasks exist, and succeeds once subtasks are completed."""
    headers = create_user_headers("completionconstraint@example.com")

    parent_id = client.post("/tasks", json={"title": "Parent Feature"}, headers=headers).json()["id"]
    subtask_id = client.post("/tasks", json={"title": "Subtask Work", "parent_id": parent_id}, headers=headers).json()["id"]

    # Attempting to complete parent while subtask is incomplete returns 400
    complete_parent_res1 = client.put(f"/tasks/{parent_id}", json={"status": "completed"}, headers=headers)
    assert complete_parent_res1.status_code == 400
    assert "subtask(s) remain incomplete" in complete_parent_res1.json()["detail"]

    # Complete subtask first
    client.put(f"/tasks/{subtask_id}", json={"status": "completed"}, headers=headers)

    # Now parent completion succeeds
    complete_parent_res2 = client.put(f"/tasks/{parent_id}", json={"status": "completed"}, headers=headers)
    assert complete_parent_res2.status_code == 200
    assert complete_parent_res2.json()["status"] == "completed"
