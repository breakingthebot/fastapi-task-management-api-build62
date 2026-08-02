# tests/test_auth.py
# Unit and integration tests for Authentication endpoints (/auth/register, /auth/login, /auth/me).
# Connects to: src/task_api/main.py, src/task_api/auth.py
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


def test_register_user_success():
    """Verify user registration returns 201 Created and user profile data."""
    payload = {
        "email": "alice@example.com",
        "password": "SecurePassword123!",
        "full_name": "Alice Smith"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice Smith"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email_fails():
    """Verify registering duplicate email address returns 400 Bad Request."""
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "full_name": "Duplicate User"
    }
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success():
    """Verify login returns JWT access token upon valid credentials."""
    register_payload = {
        "email": "bob@example.com",
        "password": "Password123!",
        "full_name": "Bob Jones"
    }
    client.post("/auth/register", json=register_payload)

    login_data = {
        "username": "bob@example.com",
        "password": "Password123!"
    }
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    token_json = response.json()
    assert "access_token" in token_json
    assert token_json["token_type"] == "bearer"


def test_login_invalid_password_fails():
    """Verify invalid password login attempt returns 401 Unauthorized."""
    register_payload = {
        "email": "charlie@example.com",
        "password": "RightPassword123!"
    }
    client.post("/auth/register", json=register_payload)

    login_data = {
        "username": "charlie@example.com",
        "password": "WrongPassword123!"
    }
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_current_user_profile():
    """Verify /auth/me returns authenticated user details when passing Bearer token."""
    client.post("/auth/register", json={"email": "david@example.com", "password": "Password123!"})
    login_res = client.post("/auth/login", data={"username": "david@example.com", "password": "Password123!"})
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "david@example.com"
