"""
NSS ERP — Shared test fixtures.

Provides a FastAPI TestClient backed by the local PostgreSQL database.
Tests run against the same nss.* schema used by the application.

Requirements:
  - Local PostgreSQL running with nss schema bootstrapped
  - api/.env configured with DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
  - pytest + httpx installed

Usage:
  pytest                        # run all tests
  pytest -m integration         # run only integration tests
  pytest tests/test_bootstrap.py  # run specific file
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app, limiter


@pytest.fixture(scope="module")
def client():
    """
    FastAPI TestClient scoped to the test module.

    Uses the real database connection (local PostgreSQL).
    The TestClient does not start a server — it calls the ASGI app directly.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """
    Reset the rate limiter's in-memory storage before every test.

    slowapi's Limiter is a module-level singleton (imported from
    api.main), shared across the entire pytest process — not scoped
    per test file. Without this reset, request counts accumulate
    across every test file in the run, and a test file that makes many
    requests (e.g. a dynamic-discovery-heavy suite looping over
    /members) can push the 60/minute budget over the edge and start
    getting 429s in later, unrelated tests. This used to live only in
    test_security.py, which reset the limiter for its own tests but
    left every other file's requests accumulating against the same
    global counter.
    """
    limiter.reset()
    yield
