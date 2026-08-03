# tests/test_soft_delete.py
# Automated unit & integration tests for Soft Deletes & Task Trash Bin Recovery.
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


def test_soft_delete_and_trash_bin():
    """Verify DELETE /tasks/{id} soft-deletes task and moves it to trash bin."""
    headers = create_user_headers("trashuser@example.com")
    task_id = client.post("/tasks", json={"title": "Task to Delete"}, headers=headers).json()["id"]

    # Soft delete task
    del_res = client.delete(f"/tasks/{task_id}", headers=headers)
    assert del_res.status_code == 204

    # Active task list excludes soft-deleted task
    list_res = client.get("/tasks", headers=headers)
    assert list_res.json()["total"] == 0

    # Trash bin list contains soft-deleted task
    trash_res = client.get("/trash/tasks", headers=headers)
    assert trash_res.status_code == 200
    assert trash_res.json()["total"] == 1
    assert trash_res.json()["tasks"][0]["id"] == task_id
    assert trash_res.json()["tasks"][0]["is_deleted"] is True


def test_restore_soft_deleted_task():
    """Verify restoring a soft-deleted task moves it back to active task lists."""
    headers = create_user_headers("restoreuser@example.com")
    task_id = client.post("/tasks", json={"title": "Task to Restore"}, headers=headers).json()["id"]
    client.delete(f"/tasks/{task_id}", headers=headers)

    # Restore task
    restore_res = client.post(f"/tasks/{task_id}/restore", headers=headers)
    assert restore_res.status_code == 200
    assert restore_res.json()["is_deleted"] is False

    # Active task list includes restored task
    list_res = client.get("/tasks", headers=headers)
    assert list_res.json()["total"] == 1


def test_permanently_delete_task():
    """Verify permanently deleting a task purges it from database."""
    headers = create_user_headers("purgeuser@example.com")
    task_id = client.post("/tasks", json={"title": "Task to Purge"}, headers=headers).json()["id"]
    client.delete(f"/tasks/{task_id}", headers=headers)

    # Permanently delete task
    purge_res = client.delete(f"/trash/tasks/{task_id}", headers=headers)
    assert purge_res.status_code == 204

    # Trash bin is now empty
    trash_res = client.get("/trash/tasks", headers=headers)
    assert trash_res.json()["total"] == 0
