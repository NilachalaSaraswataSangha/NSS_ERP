"""
NSS ERP — FastAPI application entry point.

Tier 0 Bootstrap + Tier 1 Foundation API + Frontend:
  - Read-only endpoints for RBAC and Foundation data verification
  - Serves frontend/ static files (Verification UI)
  - No authentication (Tier 5)
  - No ORM — raw psycopg2 against nss.* schema
  - Connects as nss_db_backend (SELECT-only privileges)

Start with:
    python3 -m uvicorn api.main:app --reload --port 8001   (macOS/Linux)
    py -m uvicorn api.main:app --reload --port 8001         (Windows)
    (run from the repository root)

URLs:
    http://localhost:8001/          → Bootstrap Verification UI
    http://localhost:8001/docs      → Swagger UI (OpenAPI)
    http://localhost:8001/api/v1/   → API endpoints
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.config import settings
from api.database import close_pool
from api.routers import bootstrap, foundation

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


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
        "Tier 0 Bootstrap + Tier 1 Foundation API. "
        "Read-only verification endpoints."
    ),
    lifespan=lifespan,
    docs_url=None if settings.DISABLE_DOCS else "/docs",
    redoc_url=None if settings.DISABLE_DOCS else "/redoc",
    openapi_url=None if settings.DISABLE_DOCS else "/openapi.json",
)

# API routes
app.include_router(bootstrap.router)
app.include_router(foundation.router)

# Frontend: serve static assets at /assets/*, index.html at /
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
