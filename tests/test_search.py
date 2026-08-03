# tests/test_search.py
# Automated unit & integration tests for Search Indexing & Full-Text Filters.
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


def test_full_text_search_title_description_comments():
    """Verify GET /tasks/search matches keywords across title, description, and comment content."""
    headers = create_user_headers("searcher@example.com")

    # Create Task 1 matching via title
    t1_res = client.post("/tasks", json={"title": "Refactor Database Schema", "description": "Cleanup tables"}, headers=headers)
    t1_id = t1_res.json()["id"]

    # Create Task 2 matching via description
    t2_res = client.post("/tasks", json={"title": "Bugfix", "description": "Fix memory leak in database engine"}, headers=headers)
    t2_id = t2_res.json()["id"]

    # Create Task 3 with comment matching keyword
    t3_res = client.post("/tasks", json={"title": "Frontend Layout", "description": "CSS tweaks"}, headers=headers)
    t3_id = t3_res.json()["id"]
    client.post(f"/tasks/{t3_id}/comments", json={"content": "Need to optimize database queries"}, headers=headers)

    # Search for "database"
    res = client.get("/tasks/search?q=database", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    found_ids = [t["id"] for t in data["tasks"]]
    assert t1_id in found_ids
    assert t2_id in found_ids
    assert t3_id in found_ids
