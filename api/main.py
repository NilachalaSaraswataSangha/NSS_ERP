"""
NSS ERP — FastAPI application entry point.

Tier 0 Bootstrap API:
  - Read-only endpoints for RBAC verification
  - No authentication (Tier 5)
  - No ORM — raw psycopg2 against nss.* schema
  - Connects as nss_db_backend (SELECT-only privileges)

Start with:
    uvicorn api.main:app --reload --port 8001
    (run from the repository root)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.database import close_pool
from api.routers import bootstrap


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — clean up DB pool on shutdown."""
    yield
    close_pool()


app = FastAPI(
    title="NSS ERP API",
    version="0.1.0",
    description=(
        "Nilachala Saraswata Sangha ERP — Tier 0 Bootstrap API. "
        "Read-only RBAC verification endpoints."
    ),
    lifespan=lifespan,
)

app.include_router(bootstrap.router)
