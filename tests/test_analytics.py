# tests/test_analytics.py
# Automated unit & integration tests for Task Analytics & Dashboard Statistics.
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


def test_get_task_analytics():
    """Verify GET /analytics/tasks returns calculated total_tasks, completion_rate, and priority breakdowns."""
    headers = create_user_headers("analytics_user@example.com")

    # Create 3 tasks (1 completed, 2 todo)
    client.post("/tasks", json={"title": "Task 1", "status": "completed", "priority": "high"}, headers=headers)
    client.post("/tasks", json={"title": "Task 2", "status": "todo", "priority": "low"}, headers=headers)
    client.post("/tasks", json={"title": "Task 3", "status": "todo", "priority": "high"}, headers=headers)

    analytics_res = client.get("/analytics/tasks", headers=headers)
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    assert data["total_tasks"] == 3
    assert data["completed_tasks"] == 1
    assert data["pending_tasks"] == 2
    assert data["completion_rate"] == 33.33
    assert data["tasks_by_priority"]["high"] == 2
    assert data["tasks_by_priority"]["low"] == 1
    assert data["tasks_by_status"]["completed"] == 1
    assert data["tasks_by_status"]["todo"] == 2
