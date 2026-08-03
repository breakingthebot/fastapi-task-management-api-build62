# tests/test_rate_limiter.py
# Automated unit & integration tests for Rate Limiting & HTTP 429 Throttling.
# Connects to: src/task_api/rate_limiter.py, src/task_api/main.py
# Created: 2026-08-02

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from task_api.database import Base, get_db
from task_api.main import app
from task_api.rate_limiter import rate_limiter

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
    rate_limiter.reset()
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    rate_limiter.reset()


client = TestClient(app)


def test_rate_limiter_unit():
    """Verify rate limiter permits allowed requests and blocks burst requests exceeding limit."""
    key = "test_user_key"
    max_reqs = 3
    window = 60

    # 3 allowed requests
    for _ in range(max_reqs):
        allowed, _ = rate_limiter.check_rate_limit(key, max_requests=max_reqs, window_seconds=window)
        assert allowed is True

    # 4th request blocked
    allowed, retry_after = rate_limiter.check_rate_limit(key, max_requests=max_reqs, window_seconds=window)
    assert allowed is False
    assert retry_after > 0


def test_login_rate_limiting_integration():
    """Verify POST /auth/login returns HTTP 429 Too Many Requests after 5 attempts."""
    # Register test user first
    client.post("/auth/register", json={"email": "ratelimit@example.com", "password": "Password123!", "full_name": "RL User"})

    # Send 5 login requests (all under limit)
    for _ in range(5):
        res = client.post("/auth/login", data={"username": "ratelimit@example.com", "password": "Password123!"})
        assert res.status_code == 200

    # 6th request triggers 429 Too Many Requests
    blocked_res = client.post("/auth/login", data={"username": "ratelimit@example.com", "password": "Password123!"})
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers
    assert "Too many login attempts" in blocked_res.json()["detail"]
