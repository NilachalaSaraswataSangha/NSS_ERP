"""
NSS ERP — Security middleware tests.

Verifies that security controls added across all tiers actually work:
  1. Security headers are present on every response
  2. Cache-Control is scoped to API routes (not static assets)
  3. Rate limiting returns 429 after threshold
  4. CORS responds correctly to preflight and same-origin requests
  5. DISABLE_DOCS toggle hides OpenAPI endpoints
  6. Content-Security-Policy is emitted with the verified directive set,
     and the frontend source stays free of the inline handlers/scripts that
     the policy blocks (Tier 5 advisory A2)
  7. DEBUG_MODE warns loudly at startup (Tier 5 advisory A5)

These tests run against the FastAPI TestClient (no network).
"""

import logging
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.integration


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

        # NOTE: deliberately NOT using `with TestClient(app) as test_client:` here.
        # Entering/exiting TestClient as a context manager fires the app's
        # lifespan shutdown handler (api/main.py -> close_pool()), which closes
        # the shared psycopg2 pool that tests/conftest.py's session-scoped
        # `_db_conn` fixture draws its connection from. That poisoned every
        # test module that ran afterward in the same pytest session with
        # "psycopg2.InterfaceError: connection already closed". A plain
        # TestClient(app) serves requests without ever running startup/shutdown.
        test_client = TestClient(app)
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


# ── Content-Security-Policy (Tier 5 advisory A2) ─────────────────────────

def _csp_directives(header_value: str) -> dict[str, list[str]]:
    """Parse a CSP header value into {directive: [source, ...]}."""
    directives: dict[str, list[str]] = {}
    for raw in header_value.split(";"):
        parts = raw.split()
        if parts:
            directives[parts[0]] = parts[1:]
    return directives


class TestContentSecurityPolicy:
    """
    Verify the Content-Security-Policy header.

    The policy is asserted directive by directive rather than as one opaque
    string, so a future tightening (e.g. dropping 'unsafe-eval' after moving
    to the Alpine CSP build) fails only the assertion it actually changes.
    """

    def test_csp_present_on_frontend_response(self, client):
        """Frontend pages must carry the CSP header."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers

    def test_csp_present_on_api_response(self, client):
        """API responses must carry the CSP header too."""
        response = client.get("/api/v1/bootstrap/health")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers

    def test_csp_locks_down_default_and_dangerous_directives(self, client):
        """default-src is self-only; plugins, framing and base hijacking blocked."""
        d = _csp_directives(client.get("/").headers["Content-Security-Policy"])

        assert d["default-src"] == ["'self'"]
        assert d["object-src"] == ["'none'"]
        assert d["frame-ancestors"] == ["'none'"]
        assert d["base-uri"] == ["'self'"]
        assert d["form-action"] == ["'self'"]
        assert d["connect-src"] == ["'self'"]
        assert d["font-src"] == ["'self'"]

    def test_csp_script_src_forbids_unsafe_inline(self, client):
        """
        The whole point of removing every inline event handler: an injected
        on*= attribute or <script> block must not be executable.
        """
        d = _csp_directives(client.get("/").headers["Content-Security-Policy"])
        assert "'unsafe-inline'" not in d["script-src"]

    def test_csp_script_src_allows_alpine(self, client):
        """
        Alpine.js is CDN-hosted (SRI-pinned) and its default build compiles
        directive expressions with new Function() — both allowances are
        required for the frontend to work at all.
        """
        d = _csp_directives(client.get("/").headers["Content-Security-Policy"])
        assert "'self'" in d["script-src"]
        assert "https://cdn.jsdelivr.net" in d["script-src"]
        assert "'unsafe-eval'" in d["script-src"]

    def test_csp_style_src_allows_inline(self, client):
        """Inline style= attributes are used throughout; nonces cannot cover them."""
        d = _csp_directives(client.get("/").headers["Content-Security-Policy"])
        assert "'unsafe-inline'" in d["style-src"]

    def test_csp_img_src_allows_data_uris(self, client):
        """tailwind.min.css embeds form-control icons as data:image/svg+xml."""
        d = _csp_directives(client.get("/").headers["Content-Security-Policy"])
        assert "data:" in d["img-src"]

    def test_csp_absent_on_swagger_docs(self, client):
        """
        Swagger UI embeds an inline <script>, so /docs is exempt. (It is
        disabled outright in production via DISABLE_DOCS.)
        """
        response = client.get("/docs")
        if response.status_code == 404:
            pytest.skip("Docs disabled via DISABLE_DOCS.")
        assert "Content-Security-Policy" not in response.headers

    def test_csp_report_only_mode(self, client, monkeypatch):
        """CSP_REPORT_ONLY switches to the non-blocking report-only header."""
        from api.config import settings

        monkeypatch.setattr(settings, "CSP_REPORT_ONLY", True)
        response = client.get("/")
        assert "Content-Security-Policy-Report-Only" in response.headers
        assert "Content-Security-Policy" not in response.headers

    def test_csp_can_be_disabled(self, client, monkeypatch):
        """CSP_ENABLED=false suppresses the header entirely (escape hatch)."""
        from api.config import settings

        monkeypatch.setattr(settings, "CSP_ENABLED", False)
        response = client.get("/")
        assert "Content-Security-Policy" not in response.headers
        assert "Content-Security-Policy-Report-Only" not in response.headers

    def test_csp_extra_origins_are_appended(self, client, monkeypatch):
        """Adding a CDN is an env change, not a code change."""
        from api.config import settings

        monkeypatch.setattr(settings, "CSP_SCRIPT_SRC_EXTRA", ["https://cdn.example.com"])
        monkeypatch.setattr(settings, "CSP_STYLE_SRC_EXTRA", ["https://style.example.com"])
        d = _csp_directives(client.get("/").headers["Content-Security-Policy"])

        assert "https://cdn.example.com" in d["script-src"]
        assert "https://style.example.com" in d["style-src"]


class TestNoInlineEventHandlers:
    """
    Source guard for the CSP: script-src omits 'unsafe-inline', so any inline
    event handler or inline <script> block in the frontend would be silently
    dead in the browser. These tests fail the suite instead.
    """

    # on*=" not preceded by - a-z @ or : — excludes Alpine's @click / x-on:,
    # hyphenated attributes, and JS property access like this.onerror.
    _HANDLER_RE = re.compile(r'[^-a-zA-Z@:]on[a-z]+\s*=\s*"')

    @staticmethod
    def _frontend_dir() -> Path:
        return Path(__file__).resolve().parents[2] / "frontend"

    def test_no_inline_event_handlers_in_html(self):
        """No on*="..." attributes in any page."""
        offenders = []
        for path in sorted(self._frontend_dir().glob("*.html")):
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                if self._HANDLER_RE.search(line):
                    offenders.append(f"{path.name}:{lineno}")

        assert not offenders, (
            "Inline event handlers found — CSP script-src omits 'unsafe-inline', "
            "so these will not fire. Use a CSS state selector or an Alpine "
            f"@event binding instead: {offenders}"
        )

    def test_no_inline_event_handlers_emitted_by_js(self):
        """
        No on*="..." in HTML-string templates built by JS either — those are
        injected via innerHTML and are equally blocked. Use the delegated
        data-nss-action hook in nss-layout.js.
        """
        offenders = []
        js_dir = self._frontend_dir() / "assets" / "js"
        for path in sorted(js_dir.glob("*.js")):
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                if self._HANDLER_RE.search(line):
                    offenders.append(f"{path.name}:{lineno}")

        assert not offenders, f"Inline event handlers emitted by JS: {offenders}"

    def test_no_inline_script_blocks_in_html(self):
        """
        No <script> without a src=. All page logic lives in /assets/js/, which
        is what lets script-src stay free of 'unsafe-inline'.
        """
        offenders = []
        for path in sorted(self._frontend_dir().glob("*.html")):
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                for match in re.finditer(r"<script(\s[^>]*)?>", line):
                    if "src=" not in (match.group(1) or ""):
                        offenders.append(f"{path.name}:{lineno}")

        assert not offenders, f"Inline <script> blocks found: {offenders}"


class TestDebugModeWarning:
    """
    Tier 5 advisory A5: DEBUG_MODE makes /auth/forgot-password echo the
    plaintext reset OTP. It defaults to off; startup must make it loud if an
    environment ever turns it on.
    """

    def test_warns_when_debug_mode_enabled(self, monkeypatch, caplog):
        from api.config import settings
        from api.main import _warn_on_insecure_settings

        monkeypatch.setattr(settings, "DEBUG_MODE", True)
        with caplog.at_level(logging.WARNING):
            _warn_on_insecure_settings()

        assert any("DEBUG_MODE is enabled" in r.getMessage() for r in caplog.records), (
            "Enabling DEBUG_MODE must emit a startup security warning."
        )

    def test_silent_when_settings_are_secure(self, monkeypatch, caplog):
        from api.config import settings
        from api.main import _warn_on_insecure_settings

        monkeypatch.setattr(settings, "DEBUG_MODE", False)
        monkeypatch.setattr(settings, "CSP_ENABLED", True)
        monkeypatch.setattr(settings, "CSP_REPORT_ONLY", False)
        with caplog.at_level(logging.WARNING):
            _warn_on_insecure_settings()

        assert not caplog.records, (
            f"Secure defaults must not warn: {[r.getMessage() for r in caplog.records]}"
        )
