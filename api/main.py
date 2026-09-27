"""
NSS ERP — FastAPI application entry point.

Tier 0 Bootstrap + Tier 1 Foundation + Tier 2 Organization + Tier 3 Person
+ Tier 4 Family + Membership + Tier 5 Authentication + Administration
API + Frontend:
  - Read-only endpoints for RBAC, Foundation, Organization, Person,
    Family, and Membership data verification
  - Tier 5: Authentication (login, JWT, password management) and
    Administration (user CRUD, role assignment, scope management)
  - Serves frontend/ static files (Verification UIs)
  - No ORM — raw psycopg2 against nss.* schema
  - Read pool (nss_db_backend) for SELECT-only endpoints
  - Write pool (nss_db_writer) for Tier 5 auth + admin endpoints

Security middleware:
  - CORS: configurable origins via CORS_ORIGINS env var
  - Rate limiting: configurable via RATE_LIMIT env var (default 60/minute)
  - Security headers: X-Content-Type-Options, X-Frame-Options, etc.
  - Docs toggle: DISABLE_DOCS=true hides /docs, /redoc, /openapi.json

Start with:
    python3 -m uvicorn api.main:app --reload --port 8001   (macOS/Linux)
    py -m uvicorn api.main:app --reload --port 8001         (Windows)
    (run from the repository root)

URLs:
    http://localhost:8001/              -> Redirects to /login
    http://localhost:8001/login         -> Login Page (Tier 5)
    http://localhost:8001/dashboard     -> Member Dashboard (Tier 5)
    http://localhost:8001/admin         -> Administration Dashboard (Tier 5)
    http://localhost:8001/register      -> Registration Page (Tier 5)
    http://localhost:8001/docs          -> Swagger UI (OpenAPI)
    http://localhost:8001/api/v1/       -> API endpoints

    The standalone /bootstrap, /foundation, /organization, /person, /family,
    and /membership verification pages have been retired — see the "Retired
    standalone verification pages" comment below. Their functionality now
    lives behind authentication in admin.html (/admin) and dashboard.html
    (/dashboard).
"""

from contextlib import asynccontextmanager
from pathlib import Path
import logging

import psycopg2
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.config import settings
from api.database import close_pool
from api.error_handlers import (
    integrity_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from api.middleware import add_security_headers
from api.routers import bootstrap, foundation, organization, person, family, membership
from api.routers import auth, admin, registration, claim_approval, audit

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Rate limiter ─────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
)


logger = logging.getLogger(__name__)


def _warn_on_insecure_settings() -> None:
    """
    Log a loud warning for each development-only setting left enabled.

    These settings are safe locally and unsafe in a deployment, and all of
    them default to off — so the warning exists to make an accidentally
    inherited environment variable visible in the startup log rather than
    to change behaviour.

    DEBUG_MODE in particular makes /auth/forgot-password echo the plaintext
    OTP back in its response (advisory A5 in
    docs/03_Solution/security/TIER5_SECURITY_AUDIT.md), which would let
    anyone who can name a login_id reset that account's password.
    """
    if settings.DEBUG_MODE:
        logger.warning(
            "SECURITY: DEBUG_MODE is enabled — /api/v1/auth/forgot-password "
            "returns the plaintext reset OTP in its response. This must never "
            "be set in a deployed environment."
        )
    if not settings.CSP_ENABLED:
        logger.warning(
            "SECURITY: CSP_ENABLED is false — no Content-Security-Policy "
            "header will be sent."
        )
    elif settings.CSP_REPORT_ONLY:
        logger.warning(
            "SECURITY: CSP_REPORT_ONLY is enabled — Content-Security-Policy "
            "violations will be reported but not blocked."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — clean up DB pool on shutdown."""
    _warn_on_insecure_settings()
    yield
    close_pool()


app = FastAPI(
    title="NSS ERP API",
    version="0.1.0",
    description=(
        "Nilachala Saraswata Sangha ERP — "
        "Tier 0–4 read-only verification + "
        "Tier 5 Authentication & Administration API."
    ),
    lifespan=lifespan,
    docs_url=None if settings.DISABLE_DOCS else "/docs",
    redoc_url=None if settings.DISABLE_DOCS else "/redoc",
    openapi_url=None if settings.DISABLE_DOCS else "/openapi.json",
)

# ── Security middleware (order matters — outermost runs first) ────────────

# 1. Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 2. CORS — only add if origins are configured
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

# 3. Security headers on every response
app.middleware("http")(add_security_headers)


# ── Error handlers ───────────────────────────────────────────────────────
# Every failure must reach the browser as a readable `detail` string, not
# a bare status code. Registered most-specific first; FastAPI's own
# HTTPException handler is more specific than any of these, so an
# endpoint's deliberate HTTPException still wins.
#
# Note on the catch-all: Starlette's ServerErrorMiddleware re-raises after
# calling the handler, so TestClient (raise_server_exceptions=True) still
# surfaces real tracebacks to pytest. Tests keep their signal.
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(psycopg2.IntegrityError, integrity_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# ── API routes ───────────────────────────────────────────────────────────
app.include_router(bootstrap.router)
app.include_router(foundation.router)
app.include_router(organization.router)
app.include_router(person.router)
app.include_router(family.router)
app.include_router(membership.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(registration.router)
app.include_router(claim_approval.router)
app.include_router(audit.router)

# ── Frontend ─────────────────────────────────────────────────────────────
# Serve static assets at /assets/*, index.html at /
# Mounted at /assets to avoid shadowing /docs and /openapi.json.
# Root "/" is an explicit route returning index.html.
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIR / "assets")),
        name="frontend-assets",
    )

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        """Redirect root to Login page."""
        return RedirectResponse(url="/login", status_code=302)

    # ── Retired standalone verification pages ──────────────────────────
    # The read-only /foundation, /organization, /person, /membership and
    # /family pages, plus the anonymous /bootstrap verification UI, have
    # been retired. Their functionality now lives behind authentication:
    # admin.html (Reference Data, Organization Hierarchy, Person Directory,
    # Member Directory, Roles & System Settings) and dashboard.html (the
    # Family tab + org-level family browser).

    # ── Tier 5: Login + Dashboard + Admin pages ─────────────────────────
    _login_path = _FRONTEND_DIR / "login.html"
    if _login_path.is_file():

        @app.get("/login", include_in_schema=False)
        async def serve_login():
            """Serve the Login page."""
            return FileResponse(str(_login_path))

    _dashboard_path = _FRONTEND_DIR / "dashboard.html"
    if _dashboard_path.is_file():

        @app.get("/dashboard", include_in_schema=False)
        async def serve_dashboard():
            """Serve the Member Dashboard."""
            return FileResponse(str(_dashboard_path))

    _admin_path = _FRONTEND_DIR / "admin.html"
    if _admin_path.is_file():

        @app.get("/admin", include_in_schema=False)
        async def serve_admin():
            """Serve the Administration Dashboard."""
            return FileResponse(str(_admin_path))

    _register_path = _FRONTEND_DIR / "register.html"
    if _register_path.is_file():

        @app.get("/register", include_in_schema=False)
        async def serve_register():
            """Serve the Registration page."""
            return FileResponse(str(_register_path))

    _forgot_password_path = _FRONTEND_DIR / "forgot-password.html"
    if _forgot_password_path.is_file():

        @app.get("/forgot-password", include_in_schema=False)
        async def serve_forgot_password():
            """Serve the Forgot Password page."""
            return FileResponse(str(_forgot_password_path))
