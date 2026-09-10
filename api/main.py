"""
NSS ERP — FastAPI application entry point.

Tier 0 Bootstrap + Tier 1 Foundation + Tier 2 Organization API + Frontend:
  - Read-only endpoints for RBAC, Foundation, and Organization data verification
  - Serves frontend/ static files (Verification UIs)
  - No authentication (Tier 5)
  - No ORM — raw psycopg2 against nss.* schema
  - Connects as nss_db_backend (SELECT-only privileges)

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
    http://localhost:8001/              -> Bootstrap Verification UI
    http://localhost:8001/foundation    -> Foundation Verification UI
    http://localhost:8001/organization  -> Organization Verification UI
    http://localhost:8001/docs          -> Swagger UI (OpenAPI)
    http://localhost:8001/api/v1/       -> API endpoints
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.config import settings
from api.database import close_pool
from api.middleware import add_security_headers
from api.routers import bootstrap, foundation, organization

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Rate limiter ─────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — clean up DB pool on shutdown."""
    yield
    close_pool()


app = FastAPI(
    title="NSS ERP API",
    version="0.1.0",
    description=(
        "Nilachala Saraswata Sangha ERP — "
        "Tier 0 Bootstrap + Tier 1 Foundation + Tier 2 Organization API. "
        "Read-only verification endpoints."
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
        allow_methods=["GET"],
        allow_headers=["*"],
    )

# 3. Security headers on every response
app.middleware("http")(add_security_headers)


# ── API routes ───────────────────────────────────────────────────────────
app.include_router(bootstrap.router)
app.include_router(foundation.router)
app.include_router(organization.router)

# ── Frontend ─────────────────────────────────────────────────────────────
# Serve static assets at /assets/*, index.html at /
# Mounted at /assets to avoid shadowing /docs and /openapi.json.
# Root "/" is an explicit route returning index.html.
if _FRONTEND_DIR.is_dir():
    _index_path = _FRONTEND_DIR / "index.html"
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIR / "assets")),
        name="frontend-assets",
    )

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        """Serve the Bootstrap Verification UI."""
        return FileResponse(str(_index_path))

    _foundation_path = _FRONTEND_DIR / "foundation.html"
    if _foundation_path.is_file():

        @app.get("/foundation", include_in_schema=False)
        async def serve_foundation():
            """Serve the Foundation Verification UI."""
            return FileResponse(str(_foundation_path))

    _organization_path = _FRONTEND_DIR / "organization.html"
    if _organization_path.is_file():

        @app.get("/organization", include_in_schema=False)
        async def serve_organization():
            """Serve the Organization Verification UI."""
            return FileResponse(str(_organization_path))
