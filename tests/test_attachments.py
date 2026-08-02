# tests/test_attachments.py
# Automated unit & integration tests for Task File Attachment endpoints and tenant isolation.
# Connects to: src/task_api/main.py, src/task_api/crud.py
# Created: 2026-08-02

import io
import os
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


def get_auth_headers(email: str = "attachuser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Attach User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_and_list_attachment():
    """Test file upload to a task and listing attachments."""
    headers = get_auth_headers("user_upload@example.com")
    task_res = client.post("/tasks", json={"title": "Task with attachment"}, headers=headers)
    task_id = task_res.json()["id"]

    # Prepare dummy file
    file_content = b"Sample text attachment content."
    files = {"file": ("notes.txt", io.BytesIO(file_content), "text/plain")}

    upload_res = client.post(f"/tasks/{task_id}/attachments", files=files, headers=headers)
    assert upload_res.status_code == 201
    attach_data = upload_res.json()
    assert attach_data["filename"] == "notes.txt"
    assert attach_data["file_size_bytes"] == len(file_content)

    # List attachments
    list_res = client.get(f"/tasks/{task_id}/attachments", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["attachments"][0]["filename"] == "notes.txt"


def test_download_attachment():
    """Test downloading an uploaded attachment."""
    headers = get_auth_headers("user_dl@example.com")
    task_res = client.post("/tasks", json={"title": "Download Task"}, headers=headers)
    task_id = task_res.json()["id"]

    file_content = b"PDF mock content 123"
    files = {"file": ("report.pdf", io.BytesIO(file_content), "application/pdf")}

    upload_res = client.post(f"/tasks/{task_id}/attachments", files=files, headers=headers)
    attachment_id = upload_res.json()["id"]

    # Download attachment
    dl_res = client.get(f"/attachments/{attachment_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.content == file_content
    assert dl_res.headers["content-type"] == "application/pdf"


def test_delete_attachment():
    """Test deleting an uploaded attachment and verifying file cleanup."""
    headers = get_auth_headers("user_del@example.com")
    task_res = client.post("/tasks", json={"title": "Delete Attachment Task"}, headers=headers)
    task_id = task_res.json()["id"]

    files = {"file": ("temp.txt", io.BytesIO(b"Delete me"), "text/plain")}
    upload_res = client.post(f"/tasks/{task_id}/attachments", files=files, headers=headers)
    attachment_id = upload_res.json()["id"]

    del_res = client.delete(f"/attachments/{attachment_id}", headers=headers)
    assert del_res.status_code == 204

    # Download attempt should return 404
    dl_res = client.get(f"/attachments/{attachment_id}/download", headers=headers)
    assert dl_res.status_code == 404


def test_attachment_tenant_isolation():
    """Verify User B cannot list, download, or delete User A's task attachments."""
    headers_a = get_auth_headers("owner_a@example.com")
    headers_b = get_auth_headers("owner_b@example.com")

    task_res = client.post("/tasks", json={"title": "User A Task"}, headers=headers_a)
    task_id = task_res.json()["id"]

    files = {"file": ("secret.doc", io.BytesIO(b"Confidential"), "text/plain")}
    upload_res = client.post(f"/tasks/{task_id}/attachments", files=files, headers=headers_a)
    attachment_id = upload_res.json()["id"]

    # User B list attachments -> 404 Not Found
    list_res_b = client.get(f"/tasks/{task_id}/attachments", headers=headers_b)
    assert list_res_b.status_code == 404

    # User B download attachment -> 404 Not Found
    dl_res_b = client.get(f"/attachments/{attachment_id}/download", headers=headers_b)
    assert dl_res_b.status_code == 404

    # User B delete attachment -> 404 Not Found
    del_res_b = client.delete(f"/attachments/{attachment_id}", headers=headers_b)
    assert del_res_b.status_code == 404
