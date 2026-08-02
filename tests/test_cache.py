# tests/test_cache.py
# Automated unit & integration tests for Response Caching and Write-Invalidation.
# Connects to: src/task_api/main.py, src/task_api/cache.py
# Created: 2026-08-02

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from task_api.database import Base, get_db
from task_api.main import app
from task_api.cache import cache_service

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
    cache_service.clear()
    yield
    Base.metadata.drop_all(bind=engine)
    cache_service.clear()


client = TestClient(app)


def get_auth_headers(email: str = "cacheuser@example.com", password: str = "Password123!") -> dict:
    """Helper creating user and returning Bearer auth headers."""
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Cache User"})
    login_res = client.post("/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cache_hit_and_miss_headers():
    """Verify first request returns X-Cache MISS and subsequent request returns X-Cache HIT."""
    headers = get_auth_headers("cache1@example.com")
    client.post("/tasks", json={"title": "Cached Task 1"}, headers=headers)

    res1 = client.get("/tasks", headers=headers)
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"

    res2 = client.get("/tasks", headers=headers)
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"
    assert res2.json() == res1.json()


def test_write_invalidation_on_task_creation():
    """Verify creating a task invalidates the cache, causing next GET /tasks to return MISS."""
    headers = get_auth_headers("cache2@example.com")
    client.post("/tasks", json={"title": "Initial Task"}, headers=headers)

    # Populate cache
    res1 = client.get("/tasks", headers=headers)
    assert res1.headers.get("X-Cache") == "MISS"

    res2 = client.get("/tasks", headers=headers)
    assert res2.headers.get("X-Cache") == "HIT"

    # Create new task -> should invalidate user cache
    client.post("/tasks", json={"title": "Second Task"}, headers=headers)

    res3 = client.get("/tasks", headers=headers)
    assert res3.headers.get("X-Cache") == "MISS"
    assert res3.json()["total"] == 2


def test_write_invalidation_on_task_update_and_delete():
    """Verify updating and deleting tasks invalidate user cache."""
    headers = get_auth_headers("cache3@example.com")
    task = client.post("/tasks", json={"title": "Task To Mutate"}, headers=headers).json()

    # Populate cache
    client.get("/tasks", headers=headers)

    # Update task -> invalidates cache
    client.put(f"/tasks/{task['id']}", json={"title": "Mutated Title"}, headers=headers)
    res_after_update = client.get("/tasks", headers=headers)
    assert res_after_update.headers.get("X-Cache") == "MISS"

    # Populate cache again
    client.get("/tasks", headers=headers)

    # Delete task -> invalidates cache
    client.delete(f"/tasks/{task['id']}", headers=headers)
    res_after_delete = client.get("/tasks", headers=headers)
    assert res_after_delete.headers.get("X-Cache") == "MISS"
    assert res_after_delete.json()["total"] == 0
