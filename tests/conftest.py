# tests/conftest.py
# Pytest shared fixtures and hooks.
# Connects to: src/task_api/rate_limiter.py
# Created: 2026-08-02

import pytest
from task_api.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    """Reset rate limiter counts before and after every test to ensure isolated testing."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()
