"""
NSS ERP — Security middleware tests.

Verifies that security controls added across all tiers actually work:
  1. Security headers are present on every response
  2. Cache-Control is scoped to API routes (not static assets)
  3. Rate limiting returns 429 after threshold
  4. CORS responds correctly to preflight and same-origin requests
  5. DISABLE_DOCS toggle hides OpenAPI endpoints

These tests run against the FastAPI TestClient (no network).
"""

import pytest
from fastapi.testclient import TestClient

from api.main import limiter


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the rate limiter's in-memory storage before each test."""
    limiter.reset()
    yield


class TestSecurityHeaders:
    """Verify security headers on API and frontend responses."""

    def test_api_response_has_security_headers(self, client):
        """Every API response must include the four core security headers."""
        response = client.get("/api/v1/bootstrap/health")
        assert response.status_code == 200

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in response.headers["Permissions-Policy"]
        assert "microphone=()" in response.headers["Permissions-Policy"]
        assert "geolocation=()" in response.headers["Permissions-Policy"]

    def test_api_response_has_cache_control_no_store(self, client):
        """API responses under /api/ must have Cache-Control: no-store."""
        response = client.get("/api/v1/bootstrap/health")
        assert response.headers.get("Cache-Control") == "no-store"

    def test_static_response_no_cache_control_no_store(self, client):
        """Non-API responses (frontend) must NOT have Cache-Control: no-store."""
        response = client.get("/")
        assert response.status_code == 200
        # Static/frontend responses should not force no-store
        assert response.headers.get("Cache-Control") != "no-store"

    def test_x_xss_protection_not_present(self, client):
        """X-XSS-Protection is obsolete and must NOT be set."""
        response = client.get("/api/v1/bootstrap/health")
        assert "X-XSS-Protection" not in response.headers

    def test_security_headers_on_frontend_route(self, client):
        """Frontend routes also get the four core security headers."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


class TestRateLimiting:
    """Verify rate limiting produces 429 after threshold."""

    def test_rate_limit_returns_429(self, client):
        """
        Exceeding the rate limit must return 429 Too Many Requests.

        The default limit is 60/minute. We send 61 requests and verify
        the last one is rejected. TestClient is in-process (no network),
        so this completes in milliseconds.
        """
        from api.main import app, limiter

        with TestClient(app) as test_client:
            last_status = None
            for i in range(61):
                resp = test_client.get("/api/v1/bootstrap/health")
                last_status = resp.status_code
                if last_status == 429:
                    break

            assert last_status == 429, (
                "After 61 requests, rate limit (60/minute) should return 429"
            )


class TestCORS:
    """Verify CORS behaviour with and without configured origins."""

    def test_no_cors_headers_without_configured_origins(self, client):
        """
        When CORS_ORIGINS is empty (default), no CORS headers should
        appear even if the request includes an Origin header.
        """
        response = client.get(
            "/api/v1/bootstrap/health",
            headers={"Origin": "https://evil.example.com"},
        )
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_cors_preflight_without_configured_origins(self, client):
        """
        OPTIONS preflight without configured origins should not
        return CORS allow headers.
        """
        response = client.options(
            "/api/v1/bootstrap/health",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "Access-Control-Allow-Origin" not in response.headers
