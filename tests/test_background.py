# tests/test_background.py
# Automated unit & integration tests for Background Tasks and CSV Export endpoints.
# Connects to: src/task_api/main.py, src/task_api/services.py
# Created: 2026-08-02

import csv
import io
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


def get_auth_headers(email: str = "bguser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "BG User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_urgent_task_triggers_background_task():
    """Verify creating a high/urgent priority task enqueues background notification without blocking."""
    headers = get_auth_headers("urgent_user@example.com")
    payload = {
        "title": "Fix Critical Production Outage",
        "description": "DB connection timeout issue",
        "priority": "urgent",
        "status": "todo"
    }
    response = client.post("/tasks", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["priority"] == "urgent"


def test_export_tasks_background_and_download():
    """Test triggering background CSV task export and downloading the output file."""
    headers = get_auth_headers("export_user@example.com")

    # Create sample tasks to export
    client.post("/tasks", json={"title": "Export Task 1", "priority": "high"}, headers=headers)
    client.post("/tasks", json={"title": "Export Task 2", "priority": "medium"}, headers=headers)

    # Trigger export
    export_res = client.post("/tasks/export", headers=headers)
    assert export_res.status_code == 202
    export_data = export_res.json()
    assert export_data["total_exported"] == 2
    filename = export_data["filename"]

    # Download exported CSV file
    dl_res = client.get(f"/exports/{filename}/download", headers=headers)
    assert dl_res.status_code == 200
    assert "text/csv" in dl_res.headers["content-type"]

    # Inspect CSV structure
    csv_text = dl_res.content.decode("utf-8")
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(reader) == 2
    titles = [row["title"] for row in reader]
    assert "Export Task 1" in titles
    assert "Export Task 2" in titles


def test_export_download_tenant_isolation():
    """Verify User B cannot download User A's export CSV file."""
    headers_a = get_auth_headers("exporter_a@example.com")
    headers_b = get_auth_headers("exporter_b@example.com")

    client.post("/tasks", json={"title": "Private Task A"}, headers=headers_a)
    export_res = client.post("/tasks/export", headers=headers_a)
    filename = export_res.json()["filename"]

    # User B download attempt -> 404 Not Found
    dl_res_b = client.get(f"/exports/{filename}/download", headers=headers_b)
    assert dl_res_b.status_code == 404
