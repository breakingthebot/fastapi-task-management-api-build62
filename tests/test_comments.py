# tests/test_comments.py
# Automated unit & integration tests for Task Comments and Discussion Threads.
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


def test_create_and_list_comments():
    """Verify posting a comment and retrieving task discussion comments."""
    headers = create_user_headers("commenter1@example.com")
    task_res = client.post("/tasks", json={"title": "Discussion Task"}, headers=headers)
    task_id = task_res.json()["id"]

    comment_payload = {"content": "This is the first comment."}
    post_res = client.post(f"/tasks/{task_id}/comments", json=comment_payload, headers=headers)
    assert post_res.status_code == 201
    c_data = post_res.json()
    assert c_data["content"] == "This is the first comment."
    assert c_data["author_email"] == "commenter1@example.com"

    # List comments
    list_res = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["comments"][0]["id"] == c_data["id"]


def test_delete_comment():
    """Verify author can delete their own comment."""
    headers = create_user_headers("commenter2@example.com")
    task_id = client.post("/tasks", json={"title": "Delete Comment Task"}, headers=headers).json()["id"]
    comment_id = client.post(f"/tasks/{task_id}/comments", json={"content": "Temporary comment"}, headers=headers).json()["id"]

    del_res = client.delete(f"/comments/{comment_id}", headers=headers)
    assert del_res.status_code == 204

    list_res = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert list_res.json()["total"] == 0


def test_comment_authorization_restrictions():
    """Verify User B cannot delete User A's comment on a private task."""
    headers_a = create_user_headers("user_a@example.com")
    headers_b = create_user_headers("user_b@example.com")

    task_id = client.post("/tasks", json={"title": "User A Private Task"}, headers=headers_a).json()["id"]
    comment_id = client.post(f"/tasks/{task_id}/comments", json={"content": "User A comment"}, headers=headers_a).json()["id"]

    # User B delete attempt -> 404/403
    del_res_b = client.delete(f"/comments/{comment_id}", headers=headers_b)
    assert del_res_b.status_code in (403, 404)
