# tests/test_tags.py
# Automated unit & integration tests for Task Tagging and multi-category labeling endpoints.
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


def get_auth_headers(email: str = "taguser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Tag User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_tags():
    """Test creating category tags and listing user tags."""
    headers = get_auth_headers("tag_creator@example.com")

    # Create tag
    tag_res = client.post("/tags", json={"name": "Work", "color": "#ff0000"}, headers=headers)
    assert tag_res.status_code == 201
    tag_data = tag_res.json()
    assert tag_data["name"] == "Work"
    assert tag_data["color"] == "#ff0000"

    # List tags
    list_res = client.get("/tags", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["tags"][0]["name"] == "Work"


def test_duplicate_tag_name_fails():
    """Verify creating duplicate tag name for the same user returns 400 Bad Request."""
    headers = get_auth_headers("tag_dup@example.com")
    client.post("/tags", json={"name": "Urgent"}, headers=headers)

    dup_res = client.post("/tags", json={"name": "Urgent"}, headers=headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]


def test_attach_and_remove_tag_from_task():
    """Test linking a tag to a task and removing tag association."""
    headers = get_auth_headers("task_tagger@example.com")

    task_res = client.post("/tasks", json={"title": "Tagged Task"}, headers=headers)
    task_id = task_res.json()["id"]

    tag_res = client.post("/tags", json={"name": "Frontend", "color": "#007bff"}, headers=headers)
    tag_id = tag_res.json()["id"]

    # Link tag to task
    attach_res = client.post(f"/tasks/{task_id}/tags/{tag_id}", headers=headers)
    assert attach_res.status_code == 200
    task_with_tags = attach_res.json()
    assert len(task_with_tags["tags"]) == 1
    assert task_with_tags["tags"][0]["name"] == "Frontend"

    # Remove tag from task
    remove_res = client.delete(f"/tasks/{task_id}/tags/{tag_id}", headers=headers)
    assert remove_res.status_code == 200
    assert len(remove_res.json()["tags"]) == 0


def test_filter_tasks_by_tag():
    """Test filtering task list by tag query parameter."""
    headers = get_auth_headers("filter_tagger@example.com")

    # Create tags
    tag_work = client.post("/tags", json={"name": "Work"}, headers=headers).json()
    tag_home = client.post("/tags", json={"name": "Personal"}, headers=headers).json()

    # Create tasks
    task1 = client.post("/tasks", json={"title": "Office Report"}, headers=headers).json()
    task2 = client.post("/tasks", json={"title": "Grocery Shopping"}, headers=headers).json()

    # Attach tags
    client.post(f"/tasks/{task1['id']}/tags/{tag_work['id']}", headers=headers)
    client.post(f"/tasks/{task2['id']}/tags/{tag_home['id']}", headers=headers)

    # Filter tasks by tag="Work"
    filter_res = client.get("/tasks?tag=Work", headers=headers)
    assert filter_res.status_code == 200
    data = filter_res.json()
    assert data["total"] == 1
    assert data["tasks"][0]["title"] == "Office Report"


def test_tag_tenant_isolation():
    """Verify User B cannot access or link User A's tags."""
    headers_a = get_auth_headers("usera_tag@example.com")
    headers_b = get_auth_headers("userb_tag@example.com")

    tag_a = client.post("/tags", json={"name": "Private Tag A"}, headers=headers_a).json()
    task_b = client.post("/tasks", json={"title": "User B Task"}, headers=headers_b).json()

    # User B attempts to attach User A's tag -> 404 Not Found
    attach_res = client.post(f"/tasks/{task_b['id']}/tags/{tag_a['id']}", headers=headers_b)
    assert attach_res.status_code == 404
