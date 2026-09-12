# API Layer — Per-File Code Explanations

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | API_CODE_EXPLANATIONS                    |
| Version     | 1.3                                      |
| Scope       | All source files under `api/` and `tests/` |
| Status      | Complete (updated: Tier 3 Person)         |

---

## 1. Purpose of this document

This document is the authoritative, current, **per-file** reference for the NSS ERP API layer —
every source file under `api/` (FastAPI, raw psycopg2, no ORM) *except* `api/middleware.py`,
which lives in its own dedicated `SECURITY_CODE_EXPLANATIONS.md` alongside the security-relevant
portions of `api/config.py` and `api/main.py`. Likewise, `tests/` has its own dedicated
`TESTING_CODE_EXPLANATIONS.md` rather than being folded in here. For each file this document
covers, it gives:

- **Requirement** — why the file exists: what problem or need it addresses, and what would
  break or be missing without it.
- **Line-by-line** — a walkthrough of the actual code, block by block, naming real functions,
  variables, and line numbers, so that someone unfamiliar with the code could reconstruct its
  behaviour from the explanation alone.

**How the files below fit together** — read this diagram first if you're new to the codebase;
every section after it explains one box in detail:

```
Uvicorn starts api.main:app
        │
        ▼
api/config.py    ── settings = Settings() reads api/.env once, at import time (§2.1)
        │
        ▼
api/main.py      ── builds the FastAPI() app, registers security middleware (see
        │            SECURITY_CODE_EXPLANATIONS.md), includes both routers, mounts the
        │            frontend (§2.3)
        │
        ▼
An HTTP request arrives for e.g. GET /api/v1/foundation/categories
        │
        ▼
api/routers/foundation.py   ── the matching @router.get(...) handler runs (§2.5)
        │                       ├─ Depends(get_connection) borrows a pooled connection
        │                       │  from api/database.py (§2.2)
        │                       ├─ runs a parameterized SELECT against nss.*
        │                       └─ zips (column names, row values) into a dict per row
        ▼
api/schemas/foundation.py   ── that dict is unpacked into a Pydantic response model
        │                       (§2.7), which validates types and becomes the JSON body
        ▼
Response returns to the client (security headers/CORS/rate-limit already applied on the
way — see SECURITY_CODE_EXPLANATIONS.md)
```

Every router handler in `bootstrap.py`/`foundation.py`/`organization.py`/`person.py` follows this
exact same shape: `Depends(get_connection)` → parameterized SQL → zip into dicts → unpack into a
schema class. Once you've read one endpoint in §2.4/§2.5, every other endpoint in the file is the
same pattern with a different table and a different response model — that repetition is
deliberate, not something to search for a shortcut around. `person.py` (§2.11) is the one file
that pulls its zip/dict/unpack step from a shared `api/helpers.py` module (`rows_to_models`/
`row_to_model`) instead of a per-router-local copy of the same two functions — the underlying
shape is unchanged.

**This document replaces three retired docs** that covered the same files but organized by
tier/feature instead of by file: `TIER0_VERTICAL_SLICE.md` (Tier 0 Bootstrap — database through
UI), `TIER1_FOUNDATION.md` (Tier 1 Foundation — schemas through UI), and `SECURITY_HARDENING.md`
(the cross-tier security middleware stack). Those three documents interleaved narration of
`api/config.py`, `api/main.py`, etc. across multiple sections because each was written when a
new tier or cross-cutting concern landed. This document instead gives each core application file
exactly one section, covering its full current behaviour regardless of which tier introduced
which part of it — with security and testing code carved out into their own peer documents (see
above) rather than folded in here. The database DDL/seed narration that lived in
`TIER0_VERTICAL_SLICE.md` (table definitions, roles, grants) is **not** duplicated here — it
belongs to `DATABASE_CODE_EXPLANATIONS.md`, not this document.

---

## 2. Files

### 2.1 `api/config.py`

**Requirement**

The application needs database credentials and a handful of security/runtime toggles
(CORS origins, rate limit, docs visibility, listen port) sourced from the environment rather than
hardcoded, so the same codebase runs unmodified against a local Postgres instance in development
and a Neon.dev instance in production. Without this file, `api/database.py` would have nowhere
to read `DB_NAME`/`DB_USER`/`DB_PASSWORD` from, and `api/main.py` would have no single place to
turn "is `CORS_ORIGINS` configured?" or "is `DISABLE_DOCS` set?" into a Python value. The
`validate()` method exists so that a missing credential fails immediately and legibly (naming
exactly which variables are absent) instead of surfacing later as an opaque `psycopg2` connection
error.

**Line-by-line**

Lines 1–8 — module docstring:

```python
"""
NSS ERP — Application configuration.

Reads database connection parameters from environment variables.
Uses python-dotenv for local development (.env file at api/ level).

No sensitive defaults — all DB parameters are required.
"""
```

States the file reads DB connection parameters from environment variables, uses
`python-dotenv` for local development, and that there are "no sensitive defaults" (i.e.
`DB_NAME`/`DB_USER`/`DB_PASSWORD` have no fallback value).

Line 10:

```python
import os
```

Used to read environment variables via `os.environ.get`.

Line 11:

```python
from pathlib import Path
```

Cross-platform path handling (works identically on macOS/Linux and Windows) to locate the
`.env` file.

Line 13:

```python
from dotenv import load_dotenv
```

Loads a `.env` file's contents into `os.environ` so the rest of the module can read them
uniformly whether they came from a real shell export or a local `.env` file.

Line 16:

```python
_env_path = Path(__file__).resolve().parent / ".env"
```

Resolves to `api/.env` regardless of the current working directory the process was started
from (`__file__` is `api/config.py`, so `.parent` is the `api/` directory).

Line 17:

```python
load_dotenv(_env_path, encoding="utf-8-sig")
```

Loads that file into `os.environ`. `encoding="utf-8-sig"` strips a UTF-8 byte-order-mark,
which some Windows editors write into `.env` files and which would otherwise corrupt the first
variable name. If the file doesn't exist, `load_dotenv` silently does nothing — the app still
works if env vars are set some other way (e.g. Render's dashboard).

Line 20:

```python
class Settings:
```

A plain class (not a Pydantic `BaseSettings`) used as a module-level configuration object.

Lines 23–27:

```python
    DB_NAME: str = os.environ.get("DB_NAME", "")
    DB_USER: str = os.environ.get("DB_USER", "")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: str = os.environ.get("DB_PORT", "5432")
```

`DB_NAME`, `DB_USER`, `DB_PASSWORD` default to `""` (empty string — deliberately no real
default, since these are required); `DB_HOST` defaults to `"localhost"`; `DB_PORT` defaults to
`"5432"` (the standard PostgreSQL port). All are read via `os.environ.get(name, default)` at
class-body evaluation time, i.e. at import time.

Line 30:

```python
    API_PORT: int = int(os.environ.get("API_PORT", "8001"))
```

The Uvicorn listen port, cast from string to `int`.

Line 31:

```python
    DISABLE_DOCS: bool = os.environ.get("DISABLE_DOCS", "").lower() in ("1", "true", "yes")
```

Reads the raw string, lowercases it, and checks membership in a small set of truthy spellings.
Anything else (including an unset variable, which reads as `""`) evaluates to `False`, so docs
are enabled by default.

Lines 34–38:

```python
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "").split(",")
        if o.strip()
    ]
```

A list comprehension that splits the `CORS_ORIGINS` env var on commas, strips whitespace from
each entry, and drops empty strings. An unset `CORS_ORIGINS` produces `[]` (empty list) — this
is the "CORS inactive" sentinel that `api/main.py` checks with `if settings.CORS_ORIGINS:`.

Line 39:

```python
    RATE_LIMIT: str = os.environ.get("RATE_LIMIT", "60/minute")
```

A rate-limit string in the `limits` library's `<count>/<period>` syntax, consumed directly by
`slowapi.Limiter`.

Lines 41–54:

```python
    def validate(self) -> None:
        """Raise if required settings are missing."""
        missing = []
        if not self.DB_NAME:
            missing.append("DB_NAME")
        if not self.DB_USER:
            missing.append("DB_USER")
        if not self.DB_PASSWORD:
            missing.append("DB_PASSWORD")
        if missing:
            raise RuntimeError(
                f"Required environment variables not set: {', '.join(missing)}. "
                f"Create api/.env or export them before starting the server."
            )
```

Builds a `missing` list by checking `DB_NAME`, `DB_USER`, `DB_PASSWORD` (only these three —
`DB_HOST`/`DB_PORT` have safe defaults so they're never "missing"). If `missing` is non-empty,
raises `RuntimeError` with a message naming every missing variable and pointing at `api/.env`
as the fix. This is called by `api/database.py::get_pool()` before the connection pool is
created — the first thing that happens on the first real database access, not at import time
(import-time validation would make it impossible to import `api.main` for tooling, e.g.
generating an OpenAPI schema, without a database configured).

Line 57:

```python
settings = Settings()
```

A module-level singleton instantiated once. Every other file that needs configuration does
`from api.config import settings` and reads its attributes; there is exactly one `Settings`
instance in the process.

---

### 2.2 `api/database.py`

**Requirement**

Every router handler needs a database connection, but opening and closing a raw TCP connection
to PostgreSQL per request would be slow and would exhaust connections under load. This file
supplies a small, dependency-injectable connection pool so FastAPI's `Depends(get_connection)`
mechanism can hand each request a pooled connection and reliably return it afterward, and a
`check_connection()` helper the `/health` endpoint uses to report liveness without leaking
internal error detail. Without this file there is no connection strategy at all — `api/main.py`
would have nothing to call on shutdown, and every router would have to invent its own
`psycopg2.connect(...)` boilerplate.

**Line-by-line**

Lines 1–8 — module docstring:

```python
"""
NSS ERP — Database connection pool.

Uses psycopg2 with a simple connection-pool pattern.
The FastAPI application connects as nss_db_backend (read-only in Tier 0).

No ORM — raw SQL queries against nss.* tables.
"""
```

States psycopg2 is used with a "simple connection-pool pattern," the app connects as
`nss_db_backend` (read-only in Tier 0/1), and there is no ORM — raw SQL against `nss.*` tables.

Line 10:

```python
import psycopg2
```

The PostgreSQL driver.

Line 11:

```python
import psycopg2.pool
```

The pooling submodule, used for `SimpleConnectionPool`.

Line 13:

```python
from api.config import settings
```

The singleton from `config.py`, read for `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`
and for calling `.validate()`.

Line 16:

```python
_pool: psycopg2.pool.SimpleConnectionPool | None = None
```

A module-level variable holding the shared pool, initialized to `None`. The `| None` union
(Python 3.10+ syntax) documents that the pool doesn't exist until first use — **lazy
initialization**.

Lines 19–33:

```python
def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """Return the shared connection pool, creating it on first use."""
    global _pool
    if _pool is None or _pool.closed:
        settings.validate()
        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
    return _pool
```

Declares `global _pool` so it can rebind the module-level variable; if `_pool is None or
_pool.closed` (i.e. never created, or previously closed), it calls `settings.validate()` (fail
fast if credentials are missing) and then constructs `psycopg2.pool.SimpleConnectionPool(...)`.
`minconn=1` keeps one connection warm at all times; `maxconn=5` caps concurrent connections to
PostgreSQL at 5. Either way, the function returns `_pool` — callers never construct a pool
themselves.

Lines 36–41:

```python
def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        _pool = None
```

Declares `global _pool`; if a pool exists and isn't already closed, calls `_pool.closeall()`
(closes every connection cleanly) and sets `_pool = None` so a later `get_pool()` call would
recreate it from scratch. Called from `api/main.py`'s `lifespan` shutdown handler.

Lines 44–60:

```python
def get_connection():
    """
    Context-manager-compatible connection getter.

    Usage as a FastAPI dependency:
        conn = get_pool().getconn()
        try:
            yield conn
        finally:
            get_pool().putconn(conn)
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)
```

A generator function used as a FastAPI dependency. Calls `get_pool()` to obtain the shared
pool, then `pool.getconn()` to borrow one connection. `yield conn` is the point where FastAPI
hands the connection to the route handler; the `finally: pool.putconn(conn)` block runs after
the request completes (successfully or with an exception), returning the connection to the
pool rather than closing it — the connection is reused across requests. The docstring (lines
45–54) spells out this exact usage pattern for anyone reading the dependency without tracing
FastAPI's internals.

Lines 63–80:

```python
def check_connection() -> bool:
    """
    Test whether the database is reachable.

    Returns True if a simple query succeeds, False otherwise.
    Does not leak connection details on failure.
    """
    try:
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            pool.putconn(conn)
    except Exception:
        return False
```

Used exclusively by the `/health` endpoint. Wrapped in a `try/except Exception: return False`
so any failure (network, auth, pool exhaustion) collapses to a boolean rather than leaking a
stack trace or connection string to the caller. Inside the `try`, it borrows a connection
(`pool.getconn()`), opens a cursor with `with conn.cursor() as cur:`, executes the simplest
possible query `SELECT 1`, and returns `True` if that succeeds. The `finally:
pool.putconn(conn)` ensures the connection is returned to the pool even if the query raises —
this `try/finally` is nested *inside* the outer `try`, so a failure to even obtain a connection
(e.g. `get_pool()` itself raising because credentials are missing) is caught by the outer
`except` without ever reaching the `finally`.

---

### 2.3 `api/main.py`

**Requirement**

Something has to be the single object Uvicorn imports and serves (`api.main:app`), the place
that wires together the connection pool lifecycle, both routers, the security middleware stack
(rate limiting, CORS, security headers), the Swagger/ReDoc/OpenAPI docs toggle, and the static
frontend. Every other API file is a component that does nothing on its own until this file
assembles it into one FastAPI application. Without it there is no running server at all — just
a collection of importable modules.

**Line-by-line**

Lines 1–26 — module docstring:

```python
"""
NSS ERP — FastAPI application entry point.

Tier 0 Bootstrap + Tier 1 Foundation API + Frontend:
  - Read-only endpoints for RBAC and Foundation data verification
  - Serves frontend/ static files (Verification UI)
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
    http://localhost:8001/          -> Bootstrap Verification UI
    http://localhost:8001/docs      -> Swagger UI (OpenAPI)
    http://localhost:8001/api/v1/   -> API endpoints
"""
```

Summarizes the file as "Tier 0 Bootstrap + Tier 1 Foundation API + Frontend," lists what it
doesn't do (no auth, no ORM), names the security middleware present, gives the exact `uvicorn`
start commands for macOS/Linux and Windows (must be run from the repository root), and the
three URLs served (`/`, `/docs`, `/api/v1/...`).

Line 28:

```python
from contextlib import asynccontextmanager
```

Decorator used to build the FastAPI `lifespan` handler.

Line 29:

```python
from pathlib import Path
```

Used below to locate `frontend/` cross-platform.

Lines 31–34:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
```

The FastAPI application class, CORS middleware, a response type for serving a single file
(`index.html`/`foundation.html`), and a mountable static-file server for `frontend/assets/`.

Lines 35–38:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
```

The rate-limiting engine (`Limiter`), the exception type it raises on breach, the ASGI
middleware that actually enforces limits on every request, and the key function that
identifies a client by IP address.

Lines 40–43:

```python
from api.config import settings
from api.database import close_pool
from api.middleware import add_security_headers
from api.routers import bootstrap, foundation
```

Pulls in configuration, the pool-shutdown function, the security-headers middleware function,
and both routers.

Line 45:

```python
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
```

Resolves to the repository's `frontend/` directory (`api/main.py`'s parent is `api/`, whose
parent is the repo root), independent of platform path separators.

Lines 49–52:

```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
)
```

A module-level `Limiter` instance keyed by client IP, with the default rate (e.g.
`"60/minute"`) taken from configuration. This same `limiter` object is imported directly by
`tests/test_security.py` to call `limiter.reset()` between tests.

Lines 55–59:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — clean up DB pool on shutdown."""
    yield
    close_pool()
```

The FastAPI lifespan context manager. Code before `yield` would run at startup (there is none
— the pool is created lazily on first DB access, not eagerly at startup); code after `yield`
runs at shutdown, here calling `close_pool()` to cleanly close every pooled connection.

Lines 62–74:

```python
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
```

Constructs the application. The three doc-related URLs each independently collapse to `None`
when `DISABLE_DOCS` is true, which makes FastAPI return 404 for `/docs`, `/redoc`, and
`/openapi.json` — hiding endpoint paths, parameter schemas, and response models from anyone
probing an unauthenticated production deployment, while leaving the actual API routes fully
functional.

Lines 78–81 (under the comment "1. Rate limiting"):

```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

`app.state.limiter = limiter` makes the limiter reachable from `SlowAPIMiddleware` via the
request's `app` reference; `app.add_exception_handler(RateLimitExceeded,
_rate_limit_exceeded_handler)` converts a `RateLimitExceeded` exception into an HTTP 429
response with a `Retry-After` header; `app.add_middleware(SlowAPIMiddleware)` is the actual
enforcement — without this call the limiter is configured but never consulted on incoming
requests (this exact omission was caught by `test_rate_limit_returns_429` during development).
Full rationale in `SECURITY_CODE_EXPLANATIONS.md` §2.3.

Lines 84–91 (under the comment "2. CORS"):

```python
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
```

CORS middleware is added **only if** at least one origin is configured; with the default
empty list, it's never added at all, so cross-origin requests get no CORS headers regardless
of what `Origin` header they send (verified by `tests/test_security.py::TestCORS`).
`allow_methods=["GET"]` matches the read-only nature of every current endpoint.

Line 94 (under the comment "3. Security headers on every response"):

```python
app.middleware("http")(add_security_headers)
```

Registers the function from `api/middleware.py` as HTTP middleware, called with function-call
syntax (rather than the `@app.middleware("http")` decorator form) because the function is
defined in a separate module. The comments above (lines 76, 93) explain middleware execution
order: middleware added later wraps middleware added earlier, so the effective request path is
Security Headers → CORS → Rate Limiting → endpoint, and the response path unwinds in reverse —
security headers see every outgoing response, including 429s and CORS preflights. Full
walkthrough of `api/middleware.py` itself: `SECURITY_CODE_EXPLANATIONS.md` §2.1.

Lines 98–99:

```python
app.include_router(bootstrap.router)
app.include_router(foundation.router)
```

Mounts all 4 Bootstrap endpoints and all 17 Foundation endpoints onto the app.

Lines 105–124:

```python
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
```

The entire frontend-serving block is conditional on the `frontend/` directory existing, so the
API still runs (e.g. in a test environment without a frontend checkout) if it's absent.
Inside: `app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIR / "assets")),
name="frontend-assets")` serves CSS/JS/images under `/assets/*` — deliberately mounted at
`/assets` rather than `/` so it can't shadow `/docs` or `/openapi.json`. `@app.get("/",
include_in_schema=False) async def serve_frontend(): return FileResponse(str(_index_path))`
serves `frontend/index.html` at the root; `include_in_schema=False` keeps this page route out
of the OpenAPI schema (it's a UI page, not an API contract). Finally, `_foundation_path =
_FRONTEND_DIR / "foundation.html"; if _foundation_path.is_file():` — same pattern, gated on the
file's existence, serving the Tier 1 Foundation Verification UI at `/foundation`.

---

### 2.4 `api/routers/bootstrap.py`

**Requirement**

Tier 0 needs 4 concrete, callable HTTP endpoints — a liveness probe and read access to the 3
Bootstrap RBAC tables (`role_master`, `permission_master`, `role_permission`) — expressed as raw
SQL against `nss.*`, translated into the Pydantic response models from `api/schemas/bootstrap.py`.
Without this file, `api/main.py` would have nothing to mount at `/api/v1/bootstrap/*`, and there
would be no way for the frontend Bootstrap Verification UI or any consumer to see the 8 frozen
roles.

**Line-by-line**

Lines 1–11 — module docstring:

```python
"""
NSS ERP — Bootstrap RBAC endpoints.

Tier 0 read-only API:
  GET /api/v1/bootstrap/health
  GET /api/v1/bootstrap/roles
  GET /api/v1/bootstrap/permissions
  GET /api/v1/bootstrap/roles/{role_pk}/permissions

No authentication. No CRUD. No speculative permissions.
"""
```

Lists the exact 4 endpoint paths and states "No authentication. No CRUD. No speculative
permissions" as an explicit design constraint.

Line 13:

```python
from uuid import UUID
```

Used to type the `role_pk` path parameter so FastAPI validates it's a well-formed UUID before
the handler runs.

Line 15:

```python
from fastapi import APIRouter, Depends, HTTPException
```

`APIRouter` groups these endpoints; `Depends` injects the pooled connection; `HTTPException`
raises 404 responses.

Lines 17–22:

```python
from api.database import check_connection, get_connection
from api.schemas.bootstrap import (
    HealthResponse,
    PermissionResponse,
    RoleResponse,
)
```

The DB helpers and the three response models this router returns.

Line 24:

```python
router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])
```

Every route declared below is automatically prefixed with `/api/v1/bootstrap` and grouped
under the "bootstrap" tag in Swagger UI.

Lines 27–39:

```python
@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Liveness/readiness probe.

    Returns database connectivity status.
    Never exposes connection details, credentials, or error messages.
    """
    db_ok = check_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
    )
```

Note this handler takes **no** `conn=Depends(get_connection)` parameter, unlike every other
endpoint in the file; it calls `check_connection()` directly, which manages its own connection
borrow/return internally. Returns a fixed two-value vocabulary (`"ok"`/`"degraded"`,
`"connected"`/`"unreachable"`) that never echoes an underlying exception message.

Lines 42–68:

```python
@router.get("/roles", response_model=list[RoleResponse])
def list_roles(conn=Depends(get_connection)) -> list[RoleResponse]:
    """
    Return all active roles from nss.role_master.

    Tier 0 state: 8 frozen roles.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role_master_pk,
                   role_code,
                   role_name,
                   role_class,
                   scope_level,
                   description,
                   display_order,
                   is_active
              FROM nss.role_master
             WHERE is_active = TRUE
             ORDER BY display_order
            """
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    return [RoleResponse(**dict(zip(columns, row))) for row in rows]
```

Opens a cursor with `with conn.cursor() as cur:`, executes the `SELECT` above against
`nss.role_master` — the `WHERE is_active = TRUE` clause is the sole soft-delete filter; there
is no `include_inactive` parameter. `columns = [desc[0] for desc in cur.description]` pulls
column names from psycopg2's cursor metadata, and `rows = cur.fetchall()` pulls the data.
`return [RoleResponse(**dict(zip(columns, row))) for row in rows]` zips column names with each
row's values into a dict, then unpacks that dict as keyword arguments into `RoleResponse`,
which validates types and produces the JSON the client sees.

Lines 71–97:

```python
@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(conn=Depends(get_connection)) -> list[PermissionResponse]:
    """
    Return all active permissions from nss.permission_master.

    Tier 0 state: empty by design — permissions are populated
    progressively with each module's vertical-slice implementation.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT permission_master_pk,
                   permission_code,
                   permission_name,
                   module_code,
                   description,
                   display_order,
                   is_active
              FROM nss.permission_master
             WHERE is_active = TRUE
             ORDER BY module_code, display_order
            """
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    return [PermissionResponse(**dict(zip(columns, row))) for row in rows]
```

Identical structure to `list_roles`, querying `nss.permission_master` with `ORDER BY
module_code, display_order`. In Tier 0 this always returns an empty list, because the
permission catalogue seed is intentionally empty — permissions are populated progressively per
module, not pre-seeded.

Lines 100–152:

```python
@router.get(
    "/roles/{role_pk}/permissions",
    response_model=list[PermissionResponse],
)
def list_role_permissions(
    role_pk: UUID,
    conn=Depends(get_connection),
) -> list[PermissionResponse]:
    """
    Return permissions assigned to a specific role via nss.role_permission.

    Tier 0 state: empty — no role-permission mappings exist yet.
    Returns 404 if the role_pk does not exist.
    """
    # Verify the role exists
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
              FROM nss.role_master
             WHERE role_master_pk = %s
               AND is_active = TRUE
            """,
            (str(role_pk),),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Role not found")

    # Fetch permissions via the junction table
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pm.permission_master_pk,
                   pm.permission_code,
                   pm.permission_name,
                   pm.module_code,
                   pm.description,
                   pm.display_order,
                   pm.is_active
              FROM nss.role_permission rp
              JOIN nss.permission_master pm
                ON pm.permission_master_pk = rp.permission_master_pk
             WHERE rp.role_master_pk = %s
               AND rp.is_active = TRUE
               AND pm.is_active = TRUE
             ORDER BY pm.module_code, pm.display_order
            """,
            (str(role_pk),),
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    return [PermissionResponse(**dict(zip(columns, row))) for row in rows]
```

`role_pk: UUID` means an unparseable path segment (e.g. `"not-a-uuid"`) is rejected by FastAPI
with 422 before this function body ever runs. The first cursor checks existence with `SELECT 1
FROM nss.role_master WHERE role_master_pk = %s AND is_active = TRUE`, parameterized with
`(str(role_pk),)` (psycopg2 requires the UUID as a string); if `cur.fetchone() is None`, it
raises `HTTPException(status_code=404, detail="Role not found")`. The second cursor, only
reached if the role exists, runs a `JOIN` — filtering `is_active` on *both* sides of the join,
so a soft-deleted permission or a soft-deleted mapping row is excluded even if the other side
is still active. The final return builds the response list the same zip/dict/unpack way as the
other two endpoints. In Tier 0 this always returns an empty list — no role-permission mappings
exist yet — but a 404 is still possible and is tested (`test_role_permissions_invalid_role`).

---

### 2.5 `api/routers/foundation.py`

**Requirement**

Tier 1 exposes 17 read-only GET endpoints across 11 of the 12 Foundation tables (Master Data,
System Configuration, Geographic, and one Runtime table) so downstream modules and the
Foundation Verification UI can browse master data, settings, ID-sequence definitions, and the
geographic hierarchy (country → state → district → city/village → postal code). The 12th table,
`field_change_log`, is intentionally not given an endpoint here — audit data requires
authentication, deferred to Tier 5 — and `TestChangeLogNotExposed` in the test suite guards
against that boundary being accidentally crossed. Without this file, none of the 12 Foundation
DDL tables built in the database layer would be reachable over HTTP at all.

**Line-by-line**

Lines 1–16 — module docstring:

```python
"""
Foundation API router — Tier 1 read-only endpoints.

17 GET endpoints across 11 Foundation tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Master Data:      categories, master-data
  - System Config:    settings, sequences
  - Geographic:       countries, states, districts, cities, postal-codes,
                      postal-code-mappings
  - Runtime:          documents

field_change_log is intentionally excluded from Tier 1 — audit data
requires authentication. Deferred to Tier 5.
"""
```

States "17 GET endpoints across 11 Foundation tables," lists the four endpoint groups (Master
Data / System Config / Geographic / Runtime), and states the `field_change_log` exclusion and
its rationale explicitly.

Line 18:

```python
from uuid import UUID
```

Types every PK path/query parameter.

Line 20:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

`Query` is new relative to `bootstrap.py`: it declares optional filter query parameters with
Swagger-UI descriptions.

Lines 22–35:

```python
from api.database import get_connection
from api.schemas.foundation import (
    CategoryResponse,
    CityVillageResponse,
    CountryResponse,
    DistrictResponse,
    DocumentResponse,
    MasterDataResponse,
    PostalCodeMappingResponse,
    PostalCodeResponse,
    SequenceResponse,
    SettingResponse,
    StateResponse,
)
```

All 11 response models used by this router.

Line 37:

```python
router = APIRouter(prefix="/api/v1/foundation", tags=["foundation"])
```

Separate prefix and Swagger tag from the bootstrap router, so both mount independently in
`main.py`.

Lines 42–45:

```python
def _rows_to_models(cur, model_class):
    """Convert cursor results to a list of Pydantic models."""
    columns = [desc[0] for desc in cur.description]
    return [model_class(**dict(zip(columns, row))) for row in cur.fetchall()]
```

The "cursor → Pydantic" bridge shared by every list endpoint in this file. `columns = [desc[0]
for desc in cur.description]` reads column names from cursor metadata (never hardcoded
positions); the return line converts every returned row the same zip/dict/unpack way seen in
`bootstrap.py`, but factored into a helper so it isn't repeated 15 times. If the SQL SELECT
column list doesn't exactly match the model's field names, Pydantic raises a validation error
immediately — there is no silent truncation or renaming.

Lines 48–54:

```python
def _row_to_model(cur, model_class):
    """Convert a single cursor result to a Pydantic model, or None."""
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return model_class(**dict(zip(columns, row)))
```

The single-row counterpart, used by every detail (`/…/{pk}`) endpoint. Returning `None`
(rather than raising) lets each calling endpoint decide how to turn "not found" into an
`HTTPException(404)` at its own call site.

**Master Data group (lines 57–159, 4 endpoints):**

Lines 62–73 — `GET /categories`:

```python
@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(conn=Depends(get_connection)) -> list[CategoryResponse]:
    """List all active master categories."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT master_category_pk, category_code, category_name,
                   description, display_order, is_active
            FROM   nss.master_category
            WHERE  is_active = TRUE
            ORDER BY display_order, category_name
        """)
        return _rows_to_models(cur, CategoryResponse)
```

`list_categories(conn=Depends(get_connection))` runs the `SELECT` above and returns
`_rows_to_models(cur, CategoryResponse)`.

Lines 76–92 — `GET /categories/{master_category_pk}`:

```python
@router.get("/categories/{master_category_pk}", response_model=CategoryResponse)
def get_category(
    master_category_pk: UUID,
    conn=Depends(get_connection),
) -> CategoryResponse:
    """Get a single master category by PK."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT master_category_pk, category_code, category_name,
                   description, display_order, is_active
            FROM   nss.master_category
            WHERE  master_category_pk = %s AND is_active = TRUE
        """, (str(master_category_pk),))
        result = _row_to_model(cur, CategoryResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return result
```

Runs the same column list as `list_categories` with `WHERE master_category_pk = %s AND
is_active = TRUE`, parameterized with `(str(master_category_pk),)`; if `_row_to_model` returns
`None`, raises `HTTPException(404, "Category not found")`.

Lines 95–134 — `GET /master-data`:

```python
@router.get("/master-data", response_model=list[MasterDataResponse])
def list_master_data(
    category_code: str | None = Query(None, description="Filter by category code"),
    category_pk: UUID | None = Query(None, description="Filter by category PK"),
    conn=Depends(get_connection),
) -> list[MasterDataResponse]:
    """
    List all active master data values.

    Optionally filter by category_code or category_pk.
    If both are provided, category_pk takes precedence.
    """
    base_sql = """
        SELECT md.master_data_pk, md.master_category_pk,
               mc.category_code, mc.category_name,
               md.value_code, md.value_name,
               md.description, md.display_order, md.is_active
        FROM   nss.master_data md
        JOIN   nss.master_category mc
               ON mc.master_category_pk = md.master_category_pk
        WHERE  md.is_active = TRUE
          AND  mc.is_active = TRUE
    """
    params: list = []

    if category_pk is not None:
        base_sql += " AND md.master_category_pk = %s"
        params.append(str(category_pk))
    elif category_code is not None:
        base_sql += " AND mc.category_code = %s"
        params.append(category_code)

    base_sql += """
        ORDER BY mc.display_order, mc.category_name,
                 md.display_order, md.value_name
    """

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, MasterDataResponse)
```

`list_master_data(category_code: str | None = Query(...), category_pk: UUID | None =
Query(...), conn=...)` builds `base_sql` with a `JOIN nss.master_category mc ON
mc.master_category_pk = md.master_category_pk` so `category_code`/`category_name` come from
the parent row — the "JOINed parent context" pattern used throughout this file so the UI never
needs a second round-trip to resolve a parent's display name. It filters both `md.is_active`
and `mc.is_active`. The `if category_pk is not None: ... elif category_code is not None: ...`
block is dynamic WHERE-clause building — `category_pk` takes precedence when both are
supplied, and only one extra condition is ever added. All values are appended to a `params`
list and passed as `tuple(params)` to `cur.execute`, never string-interpolated — no
SQL-injection surface regardless of what a caller supplies.

Lines 137–159 — `GET /master-data/{master_data_pk}`:

```python
@router.get("/master-data/{master_data_pk}", response_model=MasterDataResponse)
def get_master_data(
    master_data_pk: UUID,
    conn=Depends(get_connection),
) -> MasterDataResponse:
    """Get a single master data value by PK (with category context)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT md.master_data_pk, md.master_category_pk,
                   mc.category_code, mc.category_name,
                   md.value_code, md.value_name,
                   md.description, md.display_order, md.is_active
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  md.master_data_pk = %s
              AND  md.is_active = TRUE
              AND  mc.is_active = TRUE
        """, (str(master_data_pk),))
        result = _row_to_model(cur, MasterDataResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Master data value not found")
        return result
```

Same JOIN and both-sides-active filter as the list endpoint, keyed by `md.master_data_pk =
%s`; 404 if `_row_to_model` returns `None`.

**System Configuration group (lines 162–222, 3 endpoints):**

Lines 167–178 — `GET /settings`:

```python
@router.get("/settings", response_model=list[SettingResponse])
def list_settings(conn=Depends(get_connection)) -> list[SettingResponse]:
    """List all active system settings."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system_setting_pk, setting_key, setting_value,
                   description, data_type, is_active
            FROM   nss.system_setting
            WHERE  is_active = TRUE
            ORDER BY setting_key
        """)
        return _rows_to_models(cur, SettingResponse)
```

Flat query (no JOIN) against `nss.system_setting`, `ORDER BY setting_key`.

Lines 181–202 — `GET /settings/{setting_key}`:

```python
@router.get("/settings/{setting_key}", response_model=SettingResponse)
def get_setting_by_key(
    setting_key: str,
    conn=Depends(get_connection),
) -> SettingResponse:
    """
    Get a single system setting by its business key.

    Settings are consumed by code using their key name
    (e.g., CURRENT_MEMBERSHIP_YEAR), not their UUID.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system_setting_pk, setting_key, setting_value,
                   description, data_type, is_active
            FROM   nss.system_setting
            WHERE  setting_key = %s AND is_active = TRUE
        """, (setting_key,))
        result = _row_to_model(cur, SettingResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Setting not found")
        return result
```

`setting_key: str`, not `UUID` — settings are looked up by their **business key** (e.g.
`CURRENT_MEMBERSHIP_YEAR`), which is how consuming code actually references them; FastAPI does
not validate the string's format, any value is accepted and simply may or may not match a row.
404 if no match.

Lines 205–222 — `GET /sequences`:

```python
@router.get("/sequences", response_model=list[SequenceResponse])
def list_sequences(conn=Depends(get_connection)) -> list[SequenceResponse]:
    """
    List all active ID sequence configurations.

    Infrastructure/verification endpoint. current_value is excluded —
    it's infrastructure state, not consumer data.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_sequence_master_pk, sequence_code, sequence_name,
                   prefix, padding_length,
                   description, is_active
            FROM   nss.id_sequence_master
            WHERE  is_active = TRUE
            ORDER BY sequence_code
        """)
        return _rows_to_models(cur, SequenceResponse)
```

Queries `nss.id_sequence_master` selecting `id_sequence_master_pk, sequence_code,
sequence_name, prefix, padding_length, description, is_active`. The docstring and the SELECT
column list both make explicit that `current_value` — a real column in the table — is **not**
selected: it is infrastructure state (the next number to be allocated), not consumer data, and
`test_current_value_not_exposed` enforces this at the response-shape level.

**Geographic group (lines 225–486, 9 endpoints):** all parent-child relationships (country →
state → district → city/village; state/country → postal code; city/village ↔ postal code) are
expressed as **flat routes with optional query-parameter filters**, not nested paths like
`/countries/{pk}/states` — chosen so the frontend can compose filters freely and so endpoint
paths aren't coupled to the data hierarchy.

Lines 230–260 — `GET /countries` and `GET /countries/{country_pk}`:

```python
@router.get("/countries", response_model=list[CountryResponse])
def list_countries(conn=Depends(get_connection)) -> list[CountryResponse]:
    """List all active countries."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT country_pk, country_code, country_name,
                   display_order, is_active
            FROM   nss.country
            WHERE  is_active = TRUE
            ORDER BY display_order, country_name
        """)
        return _rows_to_models(cur, CountryResponse)


@router.get("/countries/{country_pk}", response_model=CountryResponse)
def get_country(
    country_pk: UUID,
    conn=Depends(get_connection),
) -> CountryResponse:
    """Get a single country by PK."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT country_pk, country_code, country_name,
                   display_order, is_active
            FROM   nss.country
            WHERE  country_pk = %s AND is_active = TRUE
        """, (str(country_pk),))
        result = _row_to_model(cur, CountryResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Country not found")
        return result
```

Top of the hierarchy, no JOIN needed.

Lines 263–317 — `GET /states` and `GET /states/{state_pk}`:

```python
@router.get("/states", response_model=list[StateResponse])
def list_states(
    country_pk: UUID | None = Query(None, description="Filter by parent country"),
    conn=Depends(get_connection),
) -> list[StateResponse]:
    """
    List all active states/provinces.

    Optionally filter by parent country PK.
    """
    base_sql = """
        SELECT s.state_pk, s.country_pk,
               c.country_code, c.country_name,
               s.state_code, s.state_name,
               s.display_order, s.is_active
        FROM   nss.state s
        JOIN   nss.country c ON c.country_pk = s.country_pk
        WHERE  s.is_active = TRUE
          AND  c.is_active = TRUE
    """
    params: list = []

    if country_pk is not None:
        base_sql += " AND s.country_pk = %s"
        params.append(str(country_pk))

    base_sql += " ORDER BY c.display_order, s.display_order, s.state_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, StateResponse)


@router.get("/states/{state_pk}", response_model=StateResponse)
def get_state(
    state_pk: UUID,
    conn=Depends(get_connection),
) -> StateResponse:
    """Get a single state by PK (with country context)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.state_pk, s.country_pk,
                   c.country_code, c.country_name,
                   s.state_code, s.state_name,
                   s.display_order, s.is_active
            FROM   nss.state s
            JOIN   nss.country c ON c.country_pk = s.country_pk
            WHERE  s.state_pk = %s
              AND  s.is_active = TRUE
              AND  c.is_active = TRUE
        """, (str(state_pk),))
        result = _row_to_model(cur, StateResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="State not found")
        return result
```

`list_states(country_pk: UUID | None = Query(None, ...), ...)` joins `nss.state s` to
`nss.country c`; if `country_pk` is supplied, appends `AND s.country_pk = %s`; `ORDER BY
c.display_order, s.display_order, s.state_name`. `GET /states/{state_pk}` mirrors this with a
PK filter and 404-on-missing.

Lines 320–375 — `GET /districts` and `GET /districts/{district_pk}`:

```python
@router.get("/districts", response_model=list[DistrictResponse])
def list_districts(
    state_pk: UUID | None = Query(None, description="Filter by parent state"),
    conn=Depends(get_connection),
) -> list[DistrictResponse]:
    """
    List all active districts.

    Optionally filter by parent state PK. Without filter, returns all
    active districts (~700+ for India alone).
    """
    base_sql = """
        SELECT d.district_pk, d.state_pk,
               s.state_name,
               d.district_code, d.district_name,
               d.display_order, d.is_active
        FROM   nss.district d
        JOIN   nss.state s ON s.state_pk = d.state_pk
        WHERE  d.is_active = TRUE
          AND  s.is_active = TRUE
    """
    params: list = []

    if state_pk is not None:
        base_sql += " AND d.state_pk = %s"
        params.append(str(state_pk))

    base_sql += " ORDER BY s.state_name, d.display_order, d.district_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, DistrictResponse)


@router.get("/districts/{district_pk}", response_model=DistrictResponse)
def get_district(
    district_pk: UUID,
    conn=Depends(get_connection),
) -> DistrictResponse:
    """Get a single district by PK (with state context)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.district_pk, d.state_pk,
                   s.state_name,
                   d.district_code, d.district_name,
                   d.display_order, d.is_active
            FROM   nss.district d
            JOIN   nss.state s ON s.state_pk = d.state_pk
            WHERE  d.district_pk = %s
              AND  d.is_active = TRUE
              AND  s.is_active = TRUE
        """, (str(district_pk),))
        result = _row_to_model(cur, DistrictResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="District not found")
        return result
```

Same filter pattern joined to `nss.state` for `state_name` only (not the state's parent
country fields — the UI already has the country from the previous drill-down step). Optional
`state_pk` filter. `GET /districts/{district_pk}` mirrors it.

Lines 378–410 — `GET /cities`:

```python
@router.get("/cities", response_model=list[CityVillageResponse])
def list_cities(
    district_pk: UUID | None = Query(None, description="Filter by parent district"),
    conn=Depends(get_connection),
) -> list[CityVillageResponse]:
    """
    List all active cities/villages.

    Optionally filter by parent district PK.
    Currently returns empty — no seed data by design.
    """
    base_sql = """
        SELECT cv.city_village_pk, cv.district_pk,
               d.district_name,
               cv.city_village_code, cv.city_village_name,
               cv.city_village_type,
               cv.display_order, cv.is_active
        FROM   nss.city_village cv
        JOIN   nss.district d ON d.district_pk = cv.district_pk
        WHERE  cv.is_active = TRUE
          AND  d.is_active = TRUE
    """
    params: list = []

    if district_pk is not None:
        base_sql += " AND cv.district_pk = %s"
        params.append(str(district_pk))

    base_sql += " ORDER BY d.district_name, cv.display_order, cv.city_village_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, CityVillageResponse)
```

`list_cities(district_pk: UUID | None = Query(None, ...), ...)` joined to `nss.district` for
`district_name`; the docstring notes it "currently returns empty — no seed data by design."
There is deliberately **no** `/cities/{pk}` detail endpoint in this file.

Lines 413–445 — `GET /postal-codes`:

```python
@router.get("/postal-codes", response_model=list[PostalCodeResponse])
def list_postal_codes(
    state_pk: UUID | None = Query(None, description="Filter by state"),
    country_pk: UUID | None = Query(None, description="Filter by country"),
    conn=Depends(get_connection),
) -> list[PostalCodeResponse]:
    """
    List all active postal codes.

    Optionally filter by state or country.
    """
    base_sql = """
        SELECT pc.postal_code_pk, pc.country_pk, pc.state_pk,
               s.state_name,
               pc.postal_code, pc.post_office_name, pc.is_active
        FROM   nss.postal_code pc
        JOIN   nss.state s ON s.state_pk = pc.state_pk
        WHERE  pc.is_active = TRUE
    """
    params: list = []

    if state_pk is not None:
        base_sql += " AND pc.state_pk = %s"
        params.append(str(state_pk))
    elif country_pk is not None:
        base_sql += " AND pc.country_pk = %s"
        params.append(str(country_pk))

    base_sql += " ORDER BY pc.postal_code"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, PostalCodeResponse)
```

`list_postal_codes(state_pk: UUID | None = Query(None, ...), country_pk: UUID | None =
Query(None, ...), ...)` joined to `nss.state` for `state_name`; if `state_pk` is given it takes
precedence over `country_pk` (the `elif`) — the two filters are mutually exclusive
alternatives, not combinable. No detail endpoint.

Lines 448–485 — `GET /postal-code-mappings`:

```python
@router.get("/postal-code-mappings", response_model=list[PostalCodeMappingResponse])
def list_postal_code_mappings(
    city_village_pk: UUID | None = Query(None, description="Filter by city/village"),
    postal_code_pk: UUID | None = Query(None, description="Filter by postal code"),
    conn=Depends(get_connection),
) -> list[PostalCodeMappingResponse]:
    """
    List city/village to postal code mappings.

    Pure junction table — no is_active, no soft-delete.
    Currently returns empty — no seed data by design.
    """
    base_sql = """
        SELECT m.city_village_postal_code_map_pk,
               m.city_village_pk, cv.city_village_name,
               m.postal_code_pk, pc.postal_code
        FROM   nss.city_village_postal_code_map m
        JOIN   nss.city_village cv ON cv.city_village_pk = m.city_village_pk
        JOIN   nss.postal_code pc ON pc.postal_code_pk = m.postal_code_pk
    """
    conditions: list[str] = []
    params: list = []

    if city_village_pk is not None:
        conditions.append("m.city_village_pk = %s")
        params.append(str(city_village_pk))
    if postal_code_pk is not None:
        conditions.append("m.postal_code_pk = %s")
        params.append(str(postal_code_pk))

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)

    base_sql += " ORDER BY cv.city_village_name, pc.postal_code"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, PostalCodeMappingResponse)
```

`list_postal_code_mappings(city_village_pk: UUID | None = Query(None, ...), postal_code_pk:
UUID | None = Query(None, ...), ...)` double joins `nss.city_village_postal_code_map m` to
both `nss.city_village cv` and `nss.postal_code pc`. Unlike `postal-codes`, this builds both
filters into a `conditions` list joined with `AND` — the two filters here are **independent
and combinable** ("mappings for city X AND postal code Y"), appropriate for a junction table
lookup. No `is_active` filter anywhere in this query — the docstring and the schema both state
this table has no soft-delete. No detail endpoint.

**Runtime group (lines 489–525, 1 endpoint):**

`GET /documents`:

```python
@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    document_type_code: str | None = Query(None, description="Filter by document type code"),
    conn=Depends(get_connection),
) -> list[DocumentResponse]:
    """
    List all active documents.

    Tier 1 exposes only currently useful fields. FK fields
    (person_pk, uploaded_by_sangha_sevi_pk) excluded — targets
    don't exist yet. Response shape revisited when consuming
    modules arrive.
    Currently returns empty — documents are runtime data.
    """
    base_sql = """
        SELECT document_master_pk, document_type_code,
               document_number, document_name, storage_path,
               file_size_bytes, mime_type, version, checksum,
               description, is_active
        FROM   nss.document_master
        WHERE  is_active = TRUE
    """
    params: list = []

    if document_type_code is not None:
        base_sql += " AND document_type_code = %s"
        params.append(document_type_code)

    base_sql += " ORDER BY document_type_code, document_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, DocumentResponse)
```

`list_documents(document_type_code: str | None = Query(None, ...), ...)` against
`nss.document_master`, optionally filtered by the business-key `document_type_code` (e.g.
`"PHOTO"`). No JOINs; FK columns `person_pk` and `uploaded_by_sangha_sevi_pk` exist in the
table but are excluded from the SELECT because their target tables (Person module) don't exist
yet. The docstring states the response shape "will be revisited when consuming modules
arrive." Currently always returns an empty list — documents are runtime data, not seed data.

---

### 2.6 `api/schemas/bootstrap.py`

**Requirement**

`api/routers/bootstrap.py` needs a typed, validated shape for every JSON response it returns, and
that shape must deliberately hide internal audit columns (`created_at`,
`created_by_sangha_sevi_pk`, `updated_at`, `updated_by_sangha_sevi_pk`, `deleted_at`,
`deleted_by_sangha_sevi_pk`) that exist in the underlying `nss.role_master` /
`nss.permission_master` tables but are not consumer-facing data. Without this file the router
would either return raw dict/tuple data with no validation or type coercion, or would leak audit
metadata to any anonymous caller.

**Line-by-line**

Lines 1–9 — module docstring:

```python
"""
NSS ERP — Pydantic response schemas for Bootstrap RBAC endpoints.

These schemas define the API contract. They deliberately exclude
audit columns (created_at, *_by_sangha_sevi_pk) — those are internal.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""
```

States the schemas "define the API contract," "deliberately exclude audit columns... those are
internal," and that `ConfigDict(from_attributes=True)` is unnecessary because raw psycopg2
returns dictionaries, not ORM objects.

Line 11:

```python
from uuid import UUID
```

Pydantic serializes this as a string in JSON.

Line 13:

```python
from pydantic import BaseModel
```

Pydantic v2 base class.

Lines 16–26:

```python
class RoleResponse(BaseModel):
    """Single role from nss.role_master."""

    role_master_pk: UUID
    role_code: str
    role_name: str
    role_class: str
    scope_level: str | None
    description: str | None
    display_order: int
    is_active: bool
```

One field per non-audit column of `nss.role_master`; `str | None` (Python 3.10+ union syntax)
marks the two genuinely nullable columns.

Lines 29–38:

```python
class PermissionResponse(BaseModel):
    """Single permission from nss.permission_master."""

    permission_master_pk: UUID
    permission_code: str
    permission_name: str
    module_code: str
    description: str | None
    display_order: int
    is_active: bool
```

Same pattern, mapped to `nss.permission_master`.

Lines 41–46:

```python
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
```

The minimal two-field contract `health_check()` returns, deliberately not including anything
that could reveal connection internals.

---

### 2.7 `api/schemas/foundation.py`

**Requirement**

`api/routers/foundation.py` needs 11 typed response models — one per queried shape — covering
Master Data, System Configuration, Geographic, and Runtime data, several of which must include
fields pulled in via SQL `JOIN` (e.g. a state's parent `country_code`/`country_name`) so the
frontend can render parent context without a second API call. Without this file the router's
17 endpoints would have no `response_model=` to validate against, and there would be no single
place documenting, for instance, that `current_value` and `person_pk` are deliberately excluded
from their respective responses.

**Line-by-line**

Lines 1–9 — module docstring:

```python
"""
Pydantic response models for the Foundation API (Tier 1).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""
```

States audit columns are excluded per the Tier 0 convention, and that
`ConfigDict(from_attributes=True)` is unnecessary for the same reason as `schemas/bootstrap.py`.

Lines 11–13:

```python
from uuid import UUID

from pydantic import BaseModel
```

Same imports as `schemas/bootstrap.py`.

**Master Data Subsystem (lines 16–47, 2 models):**

Lines 20–28 — `CategoryResponse`:

```python
class CategoryResponse(BaseModel):
    """Master category — a logical group of related master values."""

    master_category_pk: UUID
    category_code: str
    category_name: str
    description: str | None
    display_order: int
    is_active: bool
```

Maps 1:1 to `nss.master_category`.

Lines 31–47 — `MasterDataResponse`:

```python
class MasterDataResponse(BaseModel):
    """
    Master data value with parent category context.

    Includes category_code and category_name via JOIN so the UI can
    display master data with its category context in a single API call.
    """

    master_data_pk: UUID
    master_category_pk: UUID
    category_code: str
    category_name: str
    value_code: str
    value_name: str
    description: str | None
    display_order: int
    is_active: bool
```

The docstring explains `category_code`/`category_name` are included "via JOIN so the UI can
display master data with its category context in a single API call."

**System Configuration Subsystem (lines 50–79, 2 models):**

Lines 54–62 — `SettingResponse`:

```python
class SettingResponse(BaseModel):
    """System-wide configurable setting."""

    system_setting_pk: UUID
    setting_key: str
    setting_value: str
    description: str | None
    data_type: str
    is_active: bool
```

`setting_value` is always a string in the API regardless of the setting's logical type;
`data_type` tells the consumer how to interpret it.

Lines 65–79 — `SequenceResponse`:

```python
class SequenceResponse(BaseModel):
    """
    ID sequence configuration for generating business identifiers.

    Infrastructure/verification endpoint. current_value is excluded —
    it's infrastructure state, not consumer data.
    """

    id_sequence_master_pk: UUID
    sequence_code: str
    sequence_name: str
    prefix: str
    padding_length: int
    description: str | None
    is_active: bool
```

The docstring states this is an "Infrastructure/verification endpoint. `current_value` is
excluded — it's infrastructure state, not consumer data." No `current_value` field at all,
matching the router's SELECT column list.

**Geographic Subsystem (lines 82–167, 6 models):**

Lines 86–93 — `CountryResponse`:

```python
class CountryResponse(BaseModel):
    """Country reference record."""

    country_pk: UUID
    country_code: str
    country_name: str
    display_order: int
    is_active: bool
```

Standalone, no JOINed fields.

Lines 96–110 — `StateResponse`:

```python
class StateResponse(BaseModel):
    """
    State/province with parent country context.

    Includes country_code and country_name via JOIN.
    """

    state_pk: UUID
    country_pk: UUID
    country_code: str
    country_name: str
    state_code: str
    state_name: str
    display_order: int
    is_active: bool
```

The docstring notes it "Includes country_code and country_name via JOIN."

Lines 113–127 — `DistrictResponse`:

```python
class DistrictResponse(BaseModel):
    """
    District with parent state context.

    Includes state_name via JOIN. Does not include country fields —
    resolve via the state's country_pk if needed.
    """

    district_pk: UUID
    state_pk: UUID
    state_name: str
    district_code: str
    district_name: str
    display_order: int
    is_active: bool
```

The docstring notes it "Includes state_name via JOIN. Does not include country fields —
resolve via the state's country_pk if needed."

Lines 130–140 — `CityVillageResponse`:

```python
class CityVillageResponse(BaseModel):
    """City/village with parent district context."""

    city_village_pk: UUID
    district_pk: UUID
    district_name: str
    city_village_code: str
    city_village_name: str
    city_village_type: str
    display_order: int
    is_active: bool
```

`city_village_type` distinguishes `CITY` from `VILLAGE`.

Lines 143–152 — `PostalCodeResponse`:

```python
class PostalCodeResponse(BaseModel):
    """Postal code with parent state context."""

    postal_code_pk: UUID
    country_pk: UUID
    state_pk: UUID
    state_name: str
    postal_code: str
    post_office_name: str | None
    is_active: bool
```

`post_office_name` is nullable — not every postal code has a named post office.

Lines 155–167 — `PostalCodeMappingResponse`:

```python
class PostalCodeMappingResponse(BaseModel):
    """
    City/village to postal code mapping (M:N junction).

    Pure junction table — no is_active, no soft-delete.
    Includes display fields from both sides via JOIN.
    """

    city_village_postal_code_map_pk: UUID
    city_village_pk: UUID
    city_village_name: str
    postal_code_pk: UUID
    postal_code: str
```

The docstring notes "Pure junction table — no is_active, no soft-delete. Includes display
fields from both sides via JOIN." — deliberately no `is_active` or `display_order` field,
unlike every other model in this file.

**Runtime Tables (lines 170–196, 1 model):**

Lines 174–196 — `DocumentResponse`:

```python
class DocumentResponse(BaseModel):
    """
    Document master record.

    Tier 1 exposes only the currently useful fields. FK fields
    (person_pk, uploaded_by_sangha_sevi_pk) are excluded — their
    targets don't exist yet. The response shape will be revisited
    when consuming modules arrive; no assumption is made here about
    the final representation.
    """

    document_master_pk: UUID
    document_type_code: str
    document_number: str | None
    document_name: str
    storage_path: str
    file_size_bytes: int | None
    mime_type: str | None
    version: int
    checksum: str | None
    description: str | None
    is_active: bool
```

The docstring states the model is intentionally shape-agnostic: "Tier 1 exposes only the
currently useful fields. FK fields (person_pk, uploaded_by_sangha_sevi_pk) are excluded — their
targets don't exist yet. ... no assumption is made here about the final representation."

---

### 2.8 `api/__init__.py`, `api/routers/__init__.py`, `api/schemas/__init__.py`

**Requirement**

Python needs each of `api/`, `api/routers/`, and `api/schemas/` to be an importable package so
statements like `from api.database import get_connection`, `from api.routers import bootstrap,
foundation`, and `from api.schemas.foundation import CategoryResponse` resolve correctly, both
when running `uvicorn api.main:app` from the repository root and when pytest imports `api.main`
in `tests/conftest.py`. Without these three files, none of those imports would work.

**Line-by-line**

All three are package markers, not code.

`api/__init__.py` has one line of content:

```python
# NSS ERP — FastAPI API Layer
```

A comment identifying the package; it defines no names and has no runtime effect beyond
marking `api/` as a package.

`api/routers/__init__.py` and `api/schemas/__init__.py` are both completely empty files —
there is no code to show for either. Their mere presence is what makes `api.routers` and
`api.schemas` importable as packages; they contribute no code, re-exports, or `__all__`
declarations. Everything imported from these packages elsewhere in the codebase is imported by
its explicit submodule path (e.g. `from api.routers import bootstrap, foundation, organization`,
not `from api.routers import router`), so there was never a need to populate these files with
re-exports.

---

### 2.9 `api/routers/organization.py`

> **v2.0 (2026-09-12):** `organization_type_master`/`organization_status_master` retired.
> `/types` and `/statuses` (and the `_ORG_SELECT` fragment and `/hierarchy` CTE) now query
> Foundation's shared `nss.master_data` JOINed to `nss.master_category`, filtered by
> `category_code = 'ORGANIZATION_TYPE'` / `'STATUS'`. `organization`'s FK columns are renamed to
> `organization_type_master_data_pk` / `status_master_data_pk`. `OrganizationStatusResponse` is
> renamed to `StatusResponse` throughout.

**Requirement**

Tier 2 exposes 6 read-only GET endpoints across `organization` plus Foundation's shared
`master_data`/`master_category` tables (for type/status) so the Organization Verification UI
and any consumer can browse type/status catalogues, list and detail organizations with full
resolved context (type name, status name, parent name, geographic names), view an
organization's direct children, and traverse the complete organizational hierarchy as a flat
list with depth. The `organization` table FKs into 5 Foundation geographic tables (country,
state, district, city_village, postal_code) — all nullable, so every geographic column is
resolved via `LEFT JOIN` rather than `JOIN`. Without this file, the `organization` DDL table
would have no HTTP surface at all.

**Line-by-line**

Lines 1–16 — module docstring:

```python
"""
Organization API router — Tier 2 read-only endpoints.

6 GET endpoints across the organization table plus Foundation
master_data (for type/status). No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Reference:   types, statuses (from master_data)
  - Core:        organizations (list, detail, children)
  - Navigation:  hierarchy (recursive CTE tree)

Organization type values are stored in Foundation master_data
under category ORGANIZATION_TYPE. Status values use the unified
ERP-wide STATUS category (shared across all modules).
"""
```

States "6 GET endpoints across the organization table plus Foundation master_data," names the
three endpoint groups (Reference / Core / Navigation), and — new in v2.0 — explicitly documents
that type/status values now live in Foundation's `master_data` rather than dedicated
Organization tables (categories `ORGANIZATION_TYPE` and the unified, cross-module `STATUS`).

Lines 18–20:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
```

Same imports as `foundation.py`: `UUID` for path parameters, `APIRouter` for grouping,
`Depends` for connection injection, `HTTPException` for 404 responses, `Query` for optional
filter parameters.

Lines 22–28:

```python
from api.database import get_connection
from api.schemas.organization import (
    OrganizationHierarchyNodeResponse,
    OrganizationResponse,
    OrganizationTypeResponse,
    StatusResponse,
)
```

All 4 response models used by this router. `StatusResponse` (renamed from
`OrganizationStatusResponse`) reflects that lifecycle status is no longer Organization-owned —
it's the shared, unified `STATUS` category from Foundation.

Line 30:

```python
router = APIRouter(prefix="/api/v1/organization", tags=["organization"])
```

Separate prefix and Swagger tag from the bootstrap and foundation routers.

Lines 35–47 — helpers:

```python
def _rows_to_models(cur, model_class):
    """Convert cursor results to a list of Pydantic models."""
    columns = [desc[0] for desc in cur.description]
    return [model_class(**dict(zip(columns, row))) for row in cur.fetchall()]


def _row_to_model(cur, model_class):
    """Convert a single cursor result to a Pydantic model, or None."""
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return model_class(**dict(zip(columns, row)))
```

Identical to the helpers in `foundation.py` — the same "cursor → Pydantic" bridge. These
are **not** imported from `foundation.py`; each router file owns its own copy, keeping the
modules independently self-contained (no cross-router import dependency).

Lines 52–105 — shared SQL fragment:

```python
_ORG_SELECT = """
    SELECT o.organization_pk,
           o.organization_id,
           o.organization_name,
           o.organization_code,
           ot.master_data_pk   AS organization_type_pk,
           ot.value_code       AS organization_type_code,
           ot.value_name       AS organization_type_name,
           os.master_data_pk   AS status_pk,
           os.value_code       AS status_code,
           os.value_name       AS status_name,
           o.parent_organization_pk,
           p.organization_name AS parent_organization_name,
           o.address_line_1,
           o.address_line_2,
           o.phone_number,
           o.mobile_number,
           o.email,
           o.org_email,
           o.website_url,
           o.org_website_url,
           o.youtube_channel_url,
           o.org_youtube_channel_url,
           o.district_pk,
           d.district_name,
           o.state_pk,
           s.state_name,
           o.country_pk,
           c.country_name,
           o.city_village_pk,
           cv.city_village_name,
           o.postal_code_pk,
           pc.postal_code,
           o.latitude,
           o.longitude,
           o.is_active
    FROM   nss.organization o
    JOIN   nss.master_data ot
           ON ot.master_data_pk = o.organization_type_master_data_pk
    JOIN   nss.master_data os
           ON os.master_data_pk = o.status_master_data_pk
    LEFT JOIN nss.organization p
           ON p.organization_pk = o.parent_organization_pk
    LEFT JOIN nss.district d
           ON d.district_pk = o.district_pk
    LEFT JOIN nss.state s
           ON s.state_pk = o.state_pk
    LEFT JOIN nss.country c
           ON c.country_pk = o.country_pk
    LEFT JOIN nss.city_village cv
           ON cv.city_village_pk = o.city_village_pk
    LEFT JOIN nss.postal_code pc
           ON pc.postal_code_pk = o.postal_code_pk
"""
```

A module-level constant holding the reusable SELECT + FROM + JOIN block shared by the list,
detail, and children endpoints. This is the Organization router's equivalent of
`foundation.py`'s inline `base_sql` fragments, but factored into a single constant because
all three endpoints use the exact same 35-column, 8-join query shape and only differ in
their WHERE clause.

The 8 JOINs:
- 2 × `JOIN` (inner) — both against `nss.master_data`, aliased `ot` (type) and `os` (status):
  every organization row has exactly one type and one status, so inner joins are correct. Unlike
  the retired dedicated tables, both joins now target the *same* `master_data` table — the
  distinction between "type" and "status" comes entirely from which FK column
  (`organization_type_master_data_pk` vs `status_master_data_pk`) drives the join, not from
  which table is joined. Note `_ORG_SELECT` does **not** itself filter `ot`/`os` by
  `category_code` — it relies on each `organization` row's FK already pointing at the correct
  category's `master_data` row (enforced at data-entry time, not by this query or by the FK
  constraint itself, which only guarantees the row exists in `master_data`, not which category
  it belongs to).
- 6 × `LEFT JOIN` — `organization p` (parent, nullable self-FK), `district`, `state`,
  `country`, `city_village`, `postal_code`: all nullable FK columns, so a `LEFT JOIN`
  ensures rows with no address or no parent still appear in results.

The aliased column `p.organization_name AS parent_organization_name` resolves the parent's
display name in the same query, so the UI never needs a separate call to look up a parent.
`ot.master_data_pk AS organization_type_pk` and `os.master_data_pk AS status_pk` (plus the
matching `value_code`/`value_name` aliases) keep the response field names stable
(`organization_type_pk/code/name`, `status_pk/code/name`) even though the underlying columns are
now `master_data`'s generic `master_data_pk`/`value_code`/`value_name` — the aliasing is what
lets `OrganizationResponse` stay decoupled from the physical schema.

**Reference Data endpoints (lines 113–156):**

Lines 113–133 — `GET /types`:

```python
@router.get("/types", response_model=list[OrganizationTypeResponse])
def list_organization_types(
    conn=Depends(get_connection),
) -> list[OrganizationTypeResponse]:
    """List all active organization types (10 frozen types from master_data)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT md.master_data_pk  AS organization_type_pk,
                   md.value_code      AS organization_type_code,
                   md.value_name      AS organization_type_name,
                   md.description,
                   md.display_order   AS sort_order,
                   md.is_active
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  mc.category_code = 'ORGANIZATION_TYPE'
              AND  md.is_active = TRUE
            ORDER BY md.display_order
        """)
        return _rows_to_models(cur, OrganizationTypeResponse)
```

Queries Foundation's `nss.master_data` JOINed to `nss.master_category`, filtered to
`category_code = 'ORGANIZATION_TYPE'`, `ORDER BY md.display_order`. This replaces the
pre-migration flat query against the now-retired `nss.organization_type_master`. Returns the 10
frozen organization types (KENDRA, NILACHALA_KUTIRA, SMRUTI_MANDIRA, ANCHALIKA_SANGHA,
ZILLA_SANGHA, SAKHA_SANGHA, SAKHA_ASANA, PARIBARIK_ASANA, PARIBARIK_SANGHA, PATHA_CHAKRA) — two
more than the pre-migration 8, since `PARIBARIK_ASANA` and `PARIBARIK_SANGHA` were added to the
`ORGANIZATION_TYPE` category during the same migration. `md.display_order` (Foundation's generic
column name) is aliased `AS sort_order` so `OrganizationTypeResponse`'s field name is unaffected
by the underlying schema change.

Lines 136–156 — `GET /statuses`:

```python
@router.get("/statuses", response_model=list[StatusResponse])
def list_statuses(
    conn=Depends(get_connection),
) -> list[StatusResponse]:
    """List all active lifecycle statuses (13 unified statuses from master_data)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT md.master_data_pk  AS status_pk,
                   md.value_code      AS status_code,
                   md.value_name      AS status_name,
                   md.description,
                   md.display_order   AS sort_order,
                   md.is_active
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  mc.category_code = 'STATUS'
              AND  md.is_active = TRUE
            ORDER BY md.display_order
        """)
        return _rows_to_models(cur, StatusResponse)
```

Identical shape to `/types`, filtered to `category_code = 'STATUS'` instead. This is the same
handler name change as the schema rename — `list_organization_statuses` became `list_statuses`,
and the docstring/route now says "lifecycle statuses" rather than "organization lifecycle
statuses," since `STATUS` is a unified category shared across modules, not owned by
Organization. Returns the 13 lifecycle statuses (PROPOSED, APPROVED, ACTIVE, INACTIVE,
SUSPENDED, LAPSED, TRANSFERRED, RESIGNED, EXPELLED, DECEASED, DISSOLVED, ARCHIVED, EXPIRED) —
more than double the pre-migration 6, since `STATUS` absorbs values that used to be split across
a hypothetical per-module `ORGANIZATION_STATUS` and Person/Membership's `MEMBERSHIP_STATUS`.

**Core CRUD-read endpoints (lines 164–244):**

Lines 164–189 — `GET /organizations`:

```python
@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    type_code: str | None = Query(None, description="Filter by organization type code"),
    status_code: str | None = Query(None, description="Filter by status code"),
    conn=Depends(get_connection),
) -> list[OrganizationResponse]:
```

Builds the query by appending `WHERE o.is_active = TRUE` to `_ORG_SELECT`, then optionally
appending `AND ot.value_code = %s` and/or `AND os.value_code = %s` (renamed from
`ot.organization_type_code`/`os.organization_status_code`, since the joined table is now
`master_data` whose value column is generically named `value_code`). Unlike Foundation's
`master-data` (which uses `elif` — mutually exclusive filters), here both filters are
**independently combinable** with `if`/`if` (not `if`/`elif`) — filtering by both type and
status simultaneously is valid. The final `ORDER BY ot.display_order, o.organization_name` also
switched from `ot.sort_order` to `ot.display_order` to match `master_data`'s column name.

Lines 192–208 — `GET /organizations/{organization_pk}`:

Same `_ORG_SELECT` with a PK filter and `AND o.is_active = TRUE`, 404 if `_row_to_model`
returns `None`.

Lines 211–244 — `GET /organizations/{organization_pk}/children`:

Two-cursor pattern (same as `bootstrap.py`'s `list_role_permissions`): the first cursor
verifies the parent organization exists with `SELECT 1 FROM nss.organization WHERE
organization_pk = %s AND is_active = TRUE`; 404 if missing. The second cursor fetches
direct children via `WHERE o.parent_organization_pk = %s AND o.is_active = TRUE`, ordered by
`ot.display_order, o.organization_name`. In the current seed state (3 root organizations, no
children), this always returns an empty list for valid parents.

**Hierarchy endpoint (lines 252–309):**

```python
@router.get("/hierarchy", response_model=list[OrganizationHierarchyNodeResponse])
def get_organization_hierarchy(
    conn=Depends(get_connection),
) -> list[OrganizationHierarchyNodeResponse]:
```

The most complex query in the codebase. `WITH RECURSIVE org_tree AS (...)` defines a
recursive CTE with two parts:

- **Anchor member** — selects root organizations (`WHERE o.parent_organization_pk IS NULL
  AND o.is_active = TRUE`), joining to `nss.master_data` (aliased `ot`/`os`) via
  `organization_type_master_data_pk`/`status_master_data_pk` for display names — the same
  master_data-based join pattern as `_ORG_SELECT`, not a separate dedicated-table join — and
  hardcoding `0 AS depth`.
- **Recursive member** — selects children by joining `nss.organization o` to `org_tree t ON
  t.organization_pk = o.parent_organization_pk` (plus the same two `master_data` joins),
  computing `t.depth + 1` for each child level. PostgreSQL executes this recursively until no
  new rows are produced.

The final `SELECT * FROM org_tree ORDER BY depth, organization_name` returns the flat list
sorted breadth-first (all depth-0 roots first, then depth-1 children, etc.). This is
deliberately a **flat** representation — the UI uses `depthIndent(depth)` (see
`UI_CODE_EXPLANATIONS.md`) to visually indent nodes, rather than receiving nested JSON.

The recursive CTE uses a **leaner column set** than `_ORG_SELECT` (10 columns vs 35) — no
address fields, no contact/online-presence fields, no geographic LEFT JOINs, no parent name resolution — because the hierarchy
view shows only the organizational structure (name, type, status, depth), not full detail.
This maps to the dedicated `OrganizationHierarchyNodeResponse` schema (§2.10), whose
`status_code`/`status_name` fields (renamed from `organization_status_code`/
`organization_status_name`) are resolved the same `os.value_code`/`os.value_name` way as
everywhere else in this router.

---

### 2.10 `api/schemas/organization.py`

> **v2.0 (2026-09-12):** `OrganizationStatusResponse` renamed to `StatusResponse` — its fields
> renamed `organization_status_pk/code/name` → `status_pk/code/name` — reflecting that status is
> now sourced from Foundation's shared, unified `STATUS` category rather than an
> Organization-owned table. `OrganizationResponse` and `OrganizationHierarchyNodeResponse`'s
> status fields are renamed to match; their `organization_type_*` fields are unchanged.

**Requirement**

`api/routers/organization.py` needs 4 typed response models: one for each reference-data
catalogue (types, statuses), one for the full organization detail (35 fields including 8
JOINed context fields and 9 contact/online-presence fields), and one for the hierarchy tree's leaner node shape (10 fields).
Without this file the Organization router would have no `response_model=` to validate
against.

**Line-by-line**

Lines 1–13 — module docstring:

```python
"""
Pydantic response models for the Organization API (Tier 2).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Organization type is sourced from Foundation master_data (category
ORGANIZATION_TYPE). Status is sourced from the unified ERP-wide
STATUS category — a single shared category used by all modules.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""
```

Same audit-column exclusion and ConfigDict note as `schemas/bootstrap.py` and
`schemas/foundation.py`, plus a new paragraph (v2.0) documenting where type/status values now
come from — Foundation's shared `master_data`, not dedicated Organization tables.

Lines 20–28 — `OrganizationTypeResponse` (6 fields):

```python
class OrganizationTypeResponse(BaseModel):
    """Organization type from nss.master_data (category: ORGANIZATION_TYPE)."""

    organization_type_pk: UUID
    organization_type_code: str
    organization_type_name: str
    description: str | None
    sort_order: int
    is_active: bool
```

Field names (`organization_type_pk/code/name`) are unchanged from before the migration — only
the docstring changed, to say the values come "from `nss.master_data` (category:
`ORGANIZATION_TYPE`)" instead of from a dedicated `organization_type_master` table. The router's
`AS organization_type_pk` / `AS organization_type_code` / `AS organization_type_name` aliasing
(§2.9) is what keeps this schema's field names stable across the underlying table swap.

Lines 31–39 — `StatusResponse` (6 fields, renamed from `OrganizationStatusResponse`):

```python
class StatusResponse(BaseModel):
    """Lifecycle status from nss.master_data (category: STATUS)."""

    status_pk: UUID
    status_code: str
    status_name: str
    description: str | None
    sort_order: int
    is_active: bool
```

Both the class name and its three identity fields (`status_pk`, `status_code`, `status_name` —
previously `organization_status_pk`, `organization_status_code`, `organization_status_name`)
dropped the `organization_` prefix, since this is no longer an Organization-specific concept: it's
the unified, ERP-wide `STATUS` category from Foundation, shared by memberships, governance, and
any future module.

Lines 42–107 — `OrganizationResponse` (35 fields):

The largest response model in the codebase. Field groups match the `_ORG_SELECT` column list:
- 4 core fields (`organization_pk`, `organization_id`, `organization_name`,
  `organization_code`).
- 3 classification fields (`organization_type_pk/code/name`) resolved from `nss.master_data`
  (category `ORGANIZATION_TYPE`) via JOIN — field names unchanged from before the migration.
- 3 lifecycle fields (`status_pk/code/name`, renamed from `organization_status_pk/code/name`)
  resolved from the same `nss.master_data` table (category `STATUS`) via a second JOIN.
- 2 hierarchy fields (`parent_organization_pk` + `parent_organization_name` via self-LEFT
  JOIN).
- 2 inline address fields (`address_line_1`, `address_line_2`).
- 4 contact fields (`phone_number`, `mobile_number`, `email` NOT NULL DEFAULT,
  `org_email` nullable).
- 4 online presence fields (`website_url` NOT NULL DEFAULT, `org_website_url` nullable,
  `youtube_channel_url` NOT NULL DEFAULT, `org_youtube_channel_url` nullable).
- 10 geographic context fields (5 FK PKs + 5 resolved names via LEFT JOINs).
- 2 coordinate fields (`latitude`, `longitude`).
- 1 `is_active`.

Every nullable field uses `UUID | None`, `str | None`, or `float | None` — matching the
LEFT JOIN / nullable-FK reality. The docstring's closing paragraph spells out the rename
explicitly: "Type fields are aliased from master_data columns for the ORGANIZATION_TYPE
category. Status fields use the unified ERP-wide STATUS category."

Lines 109–127 — `OrganizationHierarchyNodeResponse` (10 fields):

The leaner shape used by the `/hierarchy` endpoint's recursive CTE. Includes `depth: int`
(computed by the CTE as `0` for roots, `depth + 1` for children) and the type/status
display names — `organization_type_code`/`organization_type_name` plus `status_code`/
`status_name` (the latter two renamed from `organization_status_code`/
`organization_status_name`) — but no address/geographic fields. The docstring explicitly notes
"Children are not nested — the tree is returned flat."

---

### 2.11 `api/routers/person.py`

**Requirement**

Tier 3 exposes 4 read-only GET endpoints across `nss.person` and `nss.person_address` so the
Person Verification UI and any consumer can list/filter persons, view a single person's full
resolved detail, list a person's addresses, and fuzzy-search persons by name/ID/mobile number.
Person carries the ERP's first genuinely sensitive column — an encrypted Aadhaar number — so
this router's defining constraint isn't a new query shape but a security boundary: `person`'s
`aadhaar_encrypted` (BYTEA) and `aadhaar_hash` columns must never appear in any response, no
matter which endpoint or SELECT list is involved, and only the pre-truncated `aadhaar_last4` is
fit to expose for masked display (PER-BR-081). Without this file, `nss.person` and
`nss.person_address` — the two Person DDL tables — would have no HTTP surface at all, and the
Foundation-style JOIN-resolution pattern (gender/marital-status/blood-group/emergency-relationship
master data, and the full geographic chain for addresses) would have nowhere to live.

**Line-by-line**

Lines 1–16 — module docstring:

```python
"""
Person API router — Tier 3 read-only endpoints.

4 GET endpoints across 2 Person tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Core:       persons (list with filters, detail)
  - Addresses:  person addresses (per person)
  - Search:     trigram-based name/ID search

Security:
  - aadhaar_encrypted and aadhaar_hash are NEVER returned (PER-BR-081)
  - Only aadhaar_last4 is exposed for masked display
  - Audit actor FKs excluded per API convention
"""
```

States "4 GET endpoints across 2 Person tables," lists the three endpoint groups (Core /
Addresses / Search), and — unlike any prior router's docstring — dedicates an explicit
"Security:" block naming the exact business rule (PER-BR-081), the exact two forbidden columns,
and the one substitute column that is safe to expose. This is the same governance-frozen
constraint documented in `docs/01_Authoritative_References/` and enforced again in
`api/schemas/person.py` (§2.12) — belt-and-suspenders: neither the SQL nor the schema selects
the sensitive columns, so there is no single point of failure.

Lines 18–28:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.helpers import DEFAULT_LIMIT, MAX_LIMIT, row_to_model, rows_to_models
from api.schemas.person import (
    PersonAddressResponse,
    PersonResponse,
    PersonSummaryResponse,
)
```

Same FastAPI/UUID imports as `organization.py`. The notable difference: `row_to_model`/
`rows_to_models` are imported **from `api/helpers.py`** rather than redefined locally. Every
prior router (`bootstrap.py`, `foundation.py`, `organization.py`) carries its own private copy of
these two "cursor → Pydantic" functions; `person.py` is the first to consume the shared module
instead, per `api/helpers.py`'s own docstring rationale — "a single point of maintenance for any
future security hardening (e.g. column sanitisation)," which matters more here than anywhere
else given the Aadhaar-masking constraint above. `DEFAULT_LIMIT` (100) and `MAX_LIMIT` (500) are
likewise the same pagination constants centralized in `api/helpers.py`, used below by
`list_persons` instead of hardcoded literals.

Line 30:

```python
router = APIRouter(prefix="/api/v1/person", tags=["person"])
```

Separate prefix and Swagger tag from the other three routers.

**Shared SQL fragments (lines 33–143):**

```python
_PERSON_DETAIL_SELECT = """
    SELECT p.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           p.date_of_birth,
           p.date_of_death,
           p.gender_master_data_pk,
           g.value_code   AS gender_code,
           g.value_name   AS gender_name,
           p.marital_status_master_data_pk,
           ms.value_code  AS marital_status_code,
           ms.value_name  AS marital_status_name,
           p.blood_group_master_data_pk,
           bg.value_code  AS blood_group_code,
           bg.value_name  AS blood_group_name,
           p.country_phone_code,
           p.mobile_number,
           p.email,
           p.aadhaar_last4,
           p.photo_document_master_pk,
           p.emergency_contact_name,
           p.emergency_contact_phone,
           p.emergency_relationship_master_data_pk,
           er.value_code  AS emergency_relationship_code,
           er.value_name  AS emergency_relationship_name,
           p.remarks,
           p.is_active
    FROM   nss.person p
    LEFT JOIN nss.master_data g
           ON g.master_data_pk = p.gender_master_data_pk
    LEFT JOIN nss.master_data ms
           ON ms.master_data_pk = p.marital_status_master_data_pk
    LEFT JOIN nss.master_data bg
           ON bg.master_data_pk = p.blood_group_master_data_pk
    LEFT JOIN nss.master_data er
           ON er.master_data_pk = p.emergency_relationship_master_data_pk
"""
```

Unlike `organization.py`'s single `_ORG_SELECT` reused by all three core endpoints, `person.py`
defines **two** person SELECT fragments plus one address fragment — a deliberate split, not an
oversight. `_PERSON_DETAIL_SELECT` is the full 27-column shape used only by `get_person`
(single-record detail): it includes `p.aadhaar_last4` (masked, safe), `p.photo_document_master_pk`,
and the full emergency-contact block. Every master-data lookup — gender, marital status, blood
group, emergency relationship — is a `LEFT JOIN` against the same `nss.master_data` table
(aliased `g`/`ms`/`bg`/`er`), because all four of `person`'s corresponding FK columns are
nullable: a person record can exist with gender/marital-status/blood-group/emergency-relationship
left unset, and a `LEFT JOIN` (not `JOIN`) is what keeps such a row from being silently dropped.
Critically, `_PERSON_DETAIL_SELECT` never lists `p.aadhaar_encrypted` or `p.aadhaar_hash` — the
two columns the module docstring forbids — so even a future maintainer copy-pasting this SELECT
wholesale cannot accidentally leak them; the enforcement is structural, not a runtime check.

```python
_PERSON_SUMMARY_SELECT = """
    SELECT p.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           p.date_of_birth,
           p.date_of_death,
           g.value_code   AS gender_code,
           g.value_name   AS gender_name,
           ms.value_code  AS marital_status_code,
           ms.value_name  AS marital_status_name,
           bg.value_code  AS blood_group_code,
           bg.value_name  AS blood_group_name,
           p.country_phone_code,
           p.mobile_number,
           p.email,
           p.is_active
    FROM   nss.person p
    LEFT JOIN nss.master_data g
           ON g.master_data_pk = p.gender_master_data_pk
    LEFT JOIN nss.master_data ms
           ON ms.master_data_pk = p.marital_status_master_data_pk
    LEFT JOIN nss.master_data bg
           ON bg.master_data_pk = p.blood_group_master_data_pk
"""
```

`_PERSON_SUMMARY_SELECT` is the compact 17-column shape shared by `list_persons` and
`search_persons` — both multi-row endpoints where payload size matters. It drops
`aadhaar_last4`, the emergency-contact block, and `photo_document_master_pk` entirely (not just
the two forbidden Aadhaar columns — the whole sensitive/heavy block), and correspondingly has one
fewer `LEFT JOIN` (no `emergency_relationship` join, since none of its fields are selected).

```python
_ADDRESS_SELECT = """
    SELECT pa.person_address_pk,
           pa.person_pk,
           pa.address_type_master_data_pk,
           at.value_code  AS address_type_code,
           at.value_name  AS address_type_name,
           pa.address_line_1,
           pa.address_line_2,
           pa.landmark,
           pa.city_village_postal_code_map_pk,
           cv.city_village_name,
           pc.postal_code,
           d.district_name,
           s.state_name,
           c.country_name,
           pa.is_primary,
           pa.remarks,
           pa.is_active
    FROM   nss.person_address pa
    JOIN   nss.master_data at
           ON at.master_data_pk = pa.address_type_master_data_pk
    JOIN   nss.city_village_postal_code_map cvm
           ON cvm.city_village_postal_code_map_pk
              = pa.city_village_postal_code_map_pk
    LEFT JOIN nss.city_village cv
           ON cv.city_village_pk = cvm.city_village_pk
    LEFT JOIN nss.postal_code pc
           ON pc.postal_code_pk = cvm.postal_code_pk
    LEFT JOIN nss.district d
           ON d.district_pk = cv.district_pk
    LEFT JOIN nss.state s
           ON s.state_pk = d.state_pk
    LEFT JOIN nss.country c
           ON c.country_pk = s.country_pk
"""
```

`_ADDRESS_SELECT` resolves location context through a six-table JOIN chain, mixing `JOIN` and
`LEFT JOIN` deliberately rather than uniformly: `at` (address type via `master_data`) and `cvm`
(the `city_village_postal_code_map` junction row itself) use plain `JOIN`, because
`address_type_master_data_pk` and `city_village_postal_code_map_pk` are both `NOT NULL` FKs on
`person_address` — every address row is required to have a type and a location mapping, so an
inner join can't drop a valid row. From `cvm` onward, though, the chain switches to `LEFT JOIN`
for `city_village`, `postal_code`, `district`, `state`, `country` — each of those is reached by
walking the map row's own two FKs (`cvm.city_village_pk`, `cvm.postal_code_pk`) and then further
geographic parent FKs, any of which could in principle be null or point at an inactive/missing
row; a `LEFT JOIN` here means a broken or partial geographic chain degrades gracefully to `NULL`
display names rather than making the whole address disappear from the endpoint's response.

**1. PERSONS — core read (lines 146–218, 2 endpoints):**

Lines 151–193 — `GET /persons`:

```python
@router.get("/persons", response_model=list[PersonSummaryResponse])
def list_persons(
    gender_code: str | None = Query(
        None, description="Filter by gender value_code (e.g. MALE, FEMALE)"
    ),
    marital_status_code: str | None = Query(
        None, description="Filter by marital status value_code"
    ),
    blood_group_code: str | None = Query(
        None, description="Filter by blood group value_code"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    conn=Depends(get_connection),
) -> list[PersonSummaryResponse]:
    """
    List all active persons with resolved master-data context.

    Optionally filter by gender_code, marital_status_code, or
    blood_group_code. Returns a compact summary (no Aadhaar,
    emergency, or photo fields). Supports pagination via limit/offset
    (default 100, max 500).
    """
    sql = _PERSON_SUMMARY_SELECT + " WHERE p.is_active = TRUE"
    params: list = []

    if gender_code is not None:
        sql += " AND g.value_code = %s"
        params.append(gender_code)
    if marital_status_code is not None:
        sql += " AND ms.value_code = %s"
        params.append(marital_status_code)
    if blood_group_code is not None:
        sql += " AND bg.value_code = %s"
        params.append(blood_group_code)

    sql += " ORDER BY p.first_name, p.last_name"
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return rows_to_models(cur, PersonSummaryResponse)
```

`list_persons` is `person.py`'s only endpoint with query-parameter pagination in the whole API
layer — no Bootstrap, Foundation, or Organization list endpoint accepts `limit`/`offset` at all;
they return their (small, fully-seeded) tables in full. `limit: int = Query(DEFAULT_LIMIT, ge=1,
le=MAX_LIMIT, ...)` and `offset: int = Query(0, ge=0, ...)` mean an out-of-range value (e.g.
`limit=0` or `limit=10000`) is rejected by FastAPI with 422 before the handler body runs, rather
than silently clamped. All three filters (`gender_code`, `marital_status_code`,
`blood_group_code`) use `if` — not `elif` — exactly like `organization.py`'s
`type_code`/`status_code`: they are independently combinable, so a caller can filter by gender
*and* blood group in the same request. `sql += " LIMIT %s OFFSET %s"` with `params.extend([limit,
offset])` appends the pagination clause last, after all WHERE conditions and the `ORDER BY` —
`ORDER BY p.first_name, p.last_name` runs before pagination is applied, so `limit`/`offset`
paginate a *stable, name-sorted* sequence rather than an arbitrary one.

Lines 196–217 — `GET /persons/{person_pk}`:

```python
@router.get(
    "/persons/{person_pk}",
    response_model=PersonResponse,
)
def get_person(
    person_pk: UUID,
    conn=Depends(get_connection),
) -> PersonResponse:
    """
    Get a single person by PK with full resolved context.

    Includes Aadhaar last-4 (masked), emergency contact, and photo
    FK. Never returns aadhaar_encrypted or aadhaar_hash.
    """
    sql = _PERSON_DETAIL_SELECT + " WHERE p.person_pk = %s AND p.is_active = TRUE"

    with conn.cursor() as cur:
        cur.execute(sql, (str(person_pk),))
        result = row_to_model(cur, PersonResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Person not found")
        return result
```

The one endpoint that uses `_PERSON_DETAIL_SELECT`. Same PK-filter-plus-`is_active`/404 pattern
as every other detail endpoint in the codebase (`get_category`, `get_country`, `get_state`, …):
append `WHERE p.person_pk = %s AND p.is_active = TRUE`, parameterize with `(str(person_pk),)`,
and raise `HTTPException(status_code=404, detail="Person not found")` if `row_to_model` returns
`None`. The docstring repeats the security guarantee inline ("Never returns aadhaar_encrypted or
aadhaar_hash") even though it's already stated once in the module docstring — deliberate
redundancy on the one field group in the entire API surface where a silent regression would be a
data-protection incident, not just a contract mismatch.

**2. ADDRESSES (lines 220–257, 1 endpoint):**

Lines 225–257 — `GET /persons/{person_pk}/addresses`:

```python
@router.get(
    "/persons/{person_pk}/addresses",
    response_model=list[PersonAddressResponse],
)
def list_person_addresses(
    person_pk: UUID,
    conn=Depends(get_connection),
) -> list[PersonAddressResponse]:
    """
    List all active addresses for a given person.

    Resolves address type, city/village, postal code, district,
    state, and country names via JOINs. Returns 404 if the person
    does not exist.
    """
    # Verify the person exists
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.person
            WHERE  person_pk = %s AND is_active = TRUE
        """, (str(person_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Person not found")

    sql = (
        _ADDRESS_SELECT
        + " WHERE pa.person_pk = %s AND pa.is_active = TRUE"
        + " ORDER BY pa.is_primary DESC, at.value_name"
    )

    with conn.cursor() as cur:
        cur.execute(sql, (str(person_pk),))
        return rows_to_models(cur, PersonAddressResponse)
```

The same two-cursor "verify parent exists, then fetch children" pattern as
`bootstrap.py::list_role_permissions` and `organization.py`'s `/organizations/{pk}/children`: the
first cursor's `SELECT 1 FROM nss.person WHERE person_pk = %s AND is_active = TRUE` exists purely
to distinguish "person exists but has zero addresses" (empty list, 200) from "person doesn't
exist" (`HTTPException(404, "Person not found")`) — `_ADDRESS_SELECT` alone can't make that
distinction, since a `WHERE pa.person_pk = %s` with no matching rows looks identical either way.
The second cursor's `ORDER BY pa.is_primary DESC, at.value_name` puts the primary address first
(PostgreSQL sorts `TRUE` before `FALSE` under `DESC`), then breaks ties alphabetically by
resolved address-type name.

**3. SEARCH (lines 260–304, 1 endpoint):**

Lines 265–304 — `GET /search`:

```python
@router.get("/search", response_model=list[PersonSummaryResponse])
def search_persons(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Search term — matches against first_name (trigram), "
        "last_name (trigram), person_id, or mobile_number",
    ),
    conn=Depends(get_connection),
) -> list[PersonSummaryResponse]:
    """
    Search active persons by name, person_id, or mobile number.

    Uses PostgreSQL trigram similarity (pg_trgm) on first_name for
    fuzzy matching. Also matches exact prefix on person_id and
    mobile_number. Results ordered by trigram similarity (best match
    first), limited to 50 results.
    """
    sql = (
        _PERSON_SUMMARY_SELECT
        + """
        WHERE p.is_active = TRUE
          AND (
              p.first_name %% %s
              OR p.last_name %% %s
              OR p.person_id ILIKE %s
              OR p.mobile_number ILIKE %s
          )
        ORDER BY similarity(p.first_name, %s) DESC,
                 p.first_name, p.last_name
        LIMIT 50
    """
    )

    prefix_pattern = f"{q}%"

    with conn.cursor() as cur:
        cur.execute(sql, (q, q, prefix_pattern, prefix_pattern, q))
        return rows_to_models(cur, PersonSummaryResponse)
```

The only fuzzy-matching endpoint in the API layer. `q: str = Query(..., min_length=2,
max_length=100, ...)` — the `...` (Ellipsis) makes `q` required (unlike every optional filter
elsewhere, which defaults to `None`), and the length bounds mean a 1-character or absurdly long
query is rejected by FastAPI with 422 before touching the database, which also caps how expensive
a single trigram scan can be.

The WHERE clause ORs together four independent match strategies:
- `p.first_name %% %s` and `p.last_name %% %s` — the `%%` in the Python triple-quoted string is
  an *escaped* literal `%`, because this same string later goes through `cur.execute(sql,
  params)`, and psycopg2 treats a bare `%` as the start of a `%s` placeholder; the actual SQL sent
  to PostgreSQL contains a single `%`, which is `pg_trgm`'s **similarity operator** — it matches
  when the trigram similarity between the column and the bound parameter exceeds PostgreSQL's
  configured `pg_trgm.similarity_threshold` (default `0.3`). This is what makes the search
  tolerant of typos/partial names, and it requires the `pg_trgm` extension, installed by
  `database/ddl/01_extensions.sql` per `CLAUDE.md`'s bootstrap sequence.
- `p.person_id ILIKE %s` and `p.mobile_number ILIKE %s` — bound to `prefix_pattern = f"{q}%"`
  (built in Python, then passed as an ordinary bind parameter — not string-interpolated into the
  SQL, so this is not a SQL-injection surface despite the `%` wildcard living inside the bound
  value rather than the query text). This is a **prefix** match (`ILIKE 'abc%'`), not a
  substring or trigram match — appropriate for structured identifiers like `person_id` and
  `mobile_number`, where fuzzy matching would produce noise, not signal.

`ORDER BY similarity(p.first_name, %s) DESC, p.first_name, p.last_name` ranks by first-name
similarity only, even though `last_name` also participates in the WHERE-clause matching — a
result that matched purely on `last_name` trigram similarity, `person_id` prefix, or
`mobile_number` prefix is still ordered by how similar its `first_name` happens to be to `q`
(likely a low or zero score), with the two plain-alphabetical columns breaking ties. `LIMIT 50` is
hardcoded — unlike `list_persons`, this endpoint takes no `limit`/`offset` query parameters at
all. `params = (q, q, prefix_pattern, prefix_pattern, q)` is a 5-tuple whose order maps
positionally to the five `%s` placeholders in the SQL, in this order: first_name trigram,
last_name trigram, person_id prefix, mobile_number prefix, and the `similarity(...)`
`ORDER BY` argument — `q` deliberately appears three times because it's rebound at each of its
three distinct placeholder positions.

---

### 2.12 `api/schemas/person.py`

**Requirement**

`api/routers/person.py` needs three typed response models: a lean summary shape for list/search
results, a full detail shape for the single-person endpoint, and an address shape with resolved
geographic context. All three must structurally exclude `aadhaar_encrypted`/`aadhaar_hash` — the
same PER-BR-081 constraint from the router (§2.11) — so that even if a future SELECT accidentally
widened to include those columns, Pydantic's `response_model=` validation would still only pass
through the fields these classes declare; anything not declared here is silently dropped rather
than serialized. Without this file, `person.py`'s three response-model list types would have
nothing to validate against.

**Line-by-line**

Lines 1–14 — module docstring:

```python
"""
Pydantic response models for the Person API (Tier 3).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Sensitive fields excluded per PER-BR-081:
  - aadhaar_encrypted (BYTEA)  — never exposed
  - aadhaar_hash (VARCHAR)     — never exposed
Only aadhaar_last4 is returned for masked display.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""
```

Same audit-column-exclusion and `ConfigDict` notes as `schemas/bootstrap.py`/
`schemas/foundation.py`/`schemas/organization.py`, plus — new here — an explicit "Sensitive
fields excluded per PER-BR-081" block naming both forbidden columns and their BYTEA/VARCHAR
underlying types, and confirming `aadhaar_last4` is the one substitute field that is safe.

Lines 16–19:

```python
from datetime import date
from uuid import UUID

from pydantic import BaseModel
```

The first schema file in the codebase to import `date` — `person.date_of_birth` and
`person.date_of_death` are the first genuine date-typed columns exposed by any router; Pydantic
validates/serializes them as ISO-8601 date strings (`YYYY-MM-DD`) in JSON.

Lines 22–79 — `PersonResponse` (27 fields):

```python
class PersonResponse(BaseModel):
    """
    Person with resolved master-data context.

    Includes gender_name, marital_status_name, blood_group_name, and
    emergency_relationship_name via JOINs so the UI can display full
    context in a single API call.
    """

    # Identity
    person_pk: UUID
    person_id: str

    # Demographics
    first_name: str
    middle_name: str | None
    last_name: str | None
    date_of_birth: date | None
    date_of_death: date | None

    # Gender (resolved)
    gender_master_data_pk: UUID | None
    gender_code: str | None
    gender_name: str | None

    # Marital status (resolved)
    marital_status_master_data_pk: UUID | None
    marital_status_code: str | None
    marital_status_name: str | None

    # Blood group (resolved)
    blood_group_master_data_pk: UUID | None
    blood_group_code: str | None
    blood_group_name: str | None

    # Contact
    country_phone_code: str | None
    mobile_number: str | None
    email: str | None

    # Sensitive identity — masked display only
    aadhaar_last4: str | None

    # Photo
    photo_document_master_pk: UUID | None

    # Emergency contact (resolved)
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_relationship_master_data_pk: UUID | None
    emergency_relationship_code: str | None
    emergency_relationship_name: str | None

    # Other
    remarks: str | None

    # Lifecycle
    is_active: bool
```

The largest model this router needs, mapping field-for-field onto `_PERSON_DETAIL_SELECT`'s
column list, grouped by inline comments into Identity / Demographics / Gender / Marital status /
Blood group / Contact / sensitive identity / Photo / Emergency contact / Other / Lifecycle. Every
field that comes from a `LEFT JOIN` in the router (all three master-data groups, plus
`emergency_relationship`) is `UUID | None` / `str | None` — matching the nullable-FK reality —
while `person_pk`, `person_id`, `first_name`, and `is_active` (`person`'s own `NOT NULL` columns)
are unqualified. The comment `# Sensitive identity — masked display only` sits directly above the
one field (`aadhaar_last4: str | None`) that survived the PER-BR-081 filter — there is no field
named `aadhaar_encrypted` or `aadhaar_hash` anywhere in this class, which is what makes the
exclusion structural rather than a convention someone has to remember to follow.

Lines 82–106 — `PersonSummaryResponse` (16 fields):

```python
class PersonSummaryResponse(BaseModel):
    """
    Lightweight Person summary for list/search results.

    Omits Aadhaar, emergency contact, and photo details to keep
    list payloads compact.
    """

    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None
    date_of_birth: date | None
    date_of_death: date | None
    gender_code: str | None
    gender_name: str | None
    marital_status_code: str | None
    marital_status_name: str | None
    blood_group_code: str | None
    blood_group_name: str | None
    country_phone_code: str | None
    mobile_number: str | None
    email: str | None
    is_active: bool
```

Maps onto `_PERSON_SUMMARY_SELECT` and is used by both `list_persons` and `search_persons`. It
drops the three `_master_data_pk` FK fields that `PersonResponse` carries for gender/marital
status/blood group (the summary exposes only the resolved `_code`/`_name` pair, not the raw FK),
and — per the docstring — omits Aadhaar, emergency contact, and photo entirely, not just the
sensitive Aadhaar columns; this is a payload-size decision as much as a security one, since
`list_persons`/`search_persons` can return up to `MAX_LIMIT` (500) or 50 rows respectively.

Lines 109–141 — `PersonAddressResponse` (16 fields):

```python
class PersonAddressResponse(BaseModel):
    """
    Person address with resolved location context.

    Resolves address_type via master_data and location via the
    city_village_postal_code_map junction → city_village + postal_code
    + district + state + country chain.
    """

    person_address_pk: UUID
    person_pk: UUID

    # Address type (resolved)
    address_type_master_data_pk: UUID
    address_type_code: str
    address_type_name: str

    # Address fields
    address_line_1: str
    address_line_2: str | None
    landmark: str | None

    # Location (resolved through junction and geographic chain)
    city_village_postal_code_map_pk: UUID
    city_village_name: str | None
    postal_code: str | None
    district_name: str | None
    state_name: str | None
    country_name: str | None

    is_primary: bool
    remarks: str | None
    is_active: bool
```

Maps onto `_ADDRESS_SELECT`. `address_type_master_data_pk`, `address_type_code`, and
`address_type_name` are all non-nullable (`UUID`/`str`, no `| None`) — matching the router's plain
`JOIN` (not `LEFT JOIN`) against `master_data` for address type, since `person_address`'s FK there
is `NOT NULL`. By contrast, every field resolved through the `city_village_postal_code_map` →
`city_village`/`postal_code`/`district`/`state`/`country` chain (`city_village_name`,
`postal_code`, `district_name`, `state_name`, `country_name`) is `str | None` — matching the
router's `LEFT JOIN`s for that half of the chain, so a broken or partial geographic link degrades
to `None` fields rather than a validation error.

---

## 3. Cross-references

- **`docs/03_Solution/code_explanations/SECURITY_CODE_EXPLANATIONS.md`** —
  `api/middleware.py` in full, plus the security-relevant portions of `api/config.py` and
  `api/main.py` this document deliberately doesn't duplicate.
- **`docs/03_Solution/code_explanations/TESTING_CODE_EXPLANATIONS.md`** — the
  `tests/` integration suite that exercises every router/schema documented above.
- **`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`** — the Tier 1 Foundation API
  contract: the authoritative specification of what each of the 17 endpoints in
  `api/routers/foundation.py` must return, independent of this document's implementation-level
  walkthrough.
- **`docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`** — the Tier 2 Organization API
  contract: the authoritative specification of what each of the 6 endpoints in
  `api/routers/organization.py` must return, independent of this document's implementation-level
  walkthrough.
- **`docs/03_Solution/api/PERSON_API_CONTRACT.md`** — the Tier 3 Person API contract: the
  authoritative specification of what each of the 4 endpoints in `api/routers/person.py` must
  return, independent of this document's implementation-level walkthrough.
- **`docs/03_Solution/code_explanations/TIER0_SECURITY_AUDIT.md`** and
  **`TIER1_SECURITY_AUDIT.md`** — the security audit verdicts for the Bootstrap and Foundation
  API surfaces respectively. These are *not* retired by this document — they record findings and
  remediation status, which is a different concern from this document's per-file code narration,
  and continue to live alongside it in this same `code_explanations/` folder.
