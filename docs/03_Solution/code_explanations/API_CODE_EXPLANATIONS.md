# API Layer — Per-File Code Explanations

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | API_CODE_EXPLANATIONS                    |
| Version     | 1.1                                      |
| Scope       | All source files under `api/` and `tests/` |
| Status      | Complete (updated: Tier 2 Organization)   |

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

Every router handler in `bootstrap.py`/`foundation.py`/`organization.py` follows this exact same shape:
`Depends(get_connection)` → parameterized SQL → zip into dicts → unpack into a schema class.
Once you've read one endpoint in §2.4/§2.5, every other endpoint in the file is the same pattern
with a different table and a different response model — that repetition is deliberate, not
something to search for a shortcut around.

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

**Requirement**

Tier 2 exposes 6 read-only GET endpoints across 3 Organization tables
(`organization_type_master`, `organization_status_master`, `organization`) so the
Organization Verification UI and any consumer can browse type/status catalogues, list and
detail organizations with full resolved context (type name, status name, parent name,
geographic names), view an organization's direct children, and traverse the complete
organizational hierarchy as a flat list with depth. The `organization` table FKs into 5
Foundation geographic tables (country, state, district, city_village, postal_code) — all
nullable, so every geographic column is resolved via `LEFT JOIN` rather than `JOIN`.
Without this file, the 3 Organization DDL tables would have no HTTP surface at all.

**Line-by-line**

Lines 1–15 — module docstring:

```python
"""
Organization API router — Tier 2 read-only endpoints.

6 GET endpoints across 3 Organization tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Reference:   types, statuses
  - Core:        organizations (list, detail, children)
  - Navigation:  hierarchy (recursive CTE tree)

Organization depends on Foundation tables (country, state, district,
city_village, postal_code) for address resolution — these are LEFT
JOINed since address fields are nullable.
"""
```

States "6 GET endpoints across 3 Organization tables," names the three endpoint groups
(Reference / Core / Navigation), and notes the LEFT JOIN dependency on Foundation
geographic tables.

Lines 17–19:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
```

Same imports as `foundation.py`: `UUID` for path parameters, `APIRouter` for grouping,
`Depends` for connection injection, `HTTPException` for 404 responses, `Query` for optional
filter parameters.

Lines 21–27:

```python
from api.database import get_connection
from api.schemas.organization import (
    OrganizationHierarchyNodeResponse,
    OrganizationResponse,
    OrganizationStatusResponse,
    OrganizationTypeResponse,
)
```

All 4 response models used by this router.

Line 29:

```python
router = APIRouter(prefix="/api/v1/organization", tags=["organization"])
```

Separate prefix and Swagger tag from the bootstrap and foundation routers.

Lines 34–46 — helpers:

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

Lines 51–96 — shared SQL fragment:

```python
_ORG_SELECT = """
    SELECT o.organization_pk,
           o.organization_id,
           o.organization_name,
           o.organization_code,
           ot.organization_type_pk,
           ot.organization_type_code,
           ot.organization_type_name,
           os.organization_status_pk,
           os.organization_status_code,
           os.organization_status_name,
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
    JOIN   nss.organization_type_master ot
           ON ot.organization_type_pk = o.organization_type_pk
    JOIN   nss.organization_status_master os
           ON os.organization_status_pk = o.organization_status_pk
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
all three endpoints use the exact same 27-column, 8-join query shape and only differ in
their WHERE clause.

The 8 JOINs:
- 2 × `JOIN` (inner) — `organization_type_master` and `organization_status_master`: every
  organization row has exactly one type and one status, so inner joins are correct.
- 6 × `LEFT JOIN` — `organization p` (parent, nullable self-FK), `district`, `state`,
  `country`, `city_village`, `postal_code`: all nullable FK columns, so a `LEFT JOIN`
  ensures rows with no address or no parent still appear in results.

The aliased column `p.organization_name AS parent_organization_name` resolves the parent's
display name in the same query, so the UI never needs a separate call to look up a parent.

**Reference Data endpoints (lines 104–135):**

Lines 104–118 — `GET /types`:

```python
@router.get("/types", response_model=list[OrganizationTypeResponse])
def list_organization_types(
    conn=Depends(get_connection),
) -> list[OrganizationTypeResponse]:
    """List all active organization types (8 frozen types)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT organization_type_pk, organization_type_code,
                   organization_type_name, description,
                   sort_order, is_active
            FROM   nss.organization_type_master
            WHERE  is_active = TRUE
            ORDER BY sort_order
        """)
        return _rows_to_models(cur, OrganizationTypeResponse)
```

Flat query (no JOIN) against `nss.organization_type_master`, `ORDER BY sort_order`. Returns
the 8 frozen organization types (KENDRA, NILACHALA_KUTIRA, SMRUTI_MANDIRA,
ANCHALIKA_SANGHA, ZILLA_SANGHA, SAKHA_SANGHA, SAKHA_ASANA, PATHA_CHAKRA).

Lines 121–135 — `GET /statuses`:

```python
@router.get("/statuses", response_model=list[OrganizationStatusResponse])
def list_organization_statuses(
    conn=Depends(get_connection),
) -> list[OrganizationStatusResponse]:
    """List all active organization lifecycle statuses (6 statuses)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT organization_status_pk, organization_status_code,
                   organization_status_name, description,
                   sort_order, is_active
            FROM   nss.organization_status_master
            WHERE  is_active = TRUE
            ORDER BY sort_order
        """)
        return _rows_to_models(cur, OrganizationStatusResponse)
```

Flat query against `nss.organization_status_master`, `ORDER BY sort_order`. Returns the 6
lifecycle statuses (PROPOSED, APPROVED, ACTIVE, INACTIVE, SUSPENDED, ARCHIVED).

**Core CRUD-read endpoints (lines 143–223):**

Lines 143–168 — `GET /organizations`:

```python
@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    type_code: str | None = Query(None, description="Filter by organization type code"),
    status_code: str | None = Query(None, description="Filter by organization status code"),
    conn=Depends(get_connection),
) -> list[OrganizationResponse]:
```

Builds the query by appending `WHERE o.is_active = TRUE` to `_ORG_SELECT`, then optionally
appending `AND ot.organization_type_code = %s` and/or `AND os.organization_status_code =
%s`. Unlike Foundation's `master-data` (which uses `elif` — mutually exclusive filters),
here both filters are **independently combinable** with `if`/`if` (not `if`/`elif`) —
filtering by both type and status simultaneously is valid.

Lines 171–187 — `GET /organizations/{organization_pk}`:

Same `_ORG_SELECT` with a PK filter and `AND o.is_active = TRUE`, 404 if `_row_to_model`
returns `None`.

Lines 190–223 — `GET /organizations/{organization_pk}/children`:

Two-cursor pattern (same as `bootstrap.py`'s `list_role_permissions`): the first cursor
verifies the parent organization exists with `SELECT 1 FROM nss.organization WHERE
organization_pk = %s AND is_active = TRUE`; 404 if missing. The second cursor fetches
direct children via `WHERE o.parent_organization_pk = %s AND o.is_active = TRUE`. In the
current seed state (3 root organizations, no children), this always returns an empty list
for valid parents.

**Hierarchy endpoint (lines 231–288):**

```python
@router.get("/hierarchy", response_model=list[OrganizationHierarchyNodeResponse])
def get_organization_hierarchy(
    conn=Depends(get_connection),
) -> list[OrganizationHierarchyNodeResponse]:
```

The most complex query in the codebase. `WITH RECURSIVE org_tree AS (...)` defines a
recursive CTE with two parts:

- **Anchor member** — selects root organizations (`WHERE o.parent_organization_pk IS NULL
  AND o.is_active = TRUE`), joining to `organization_type_master` and
  `organization_status_master` for display names, and hardcoding `0 AS depth`.
- **Recursive member** — selects children by joining `nss.organization o` to `org_tree t ON
  t.organization_pk = o.parent_organization_pk`, computing `t.depth + 1` for each child
  level. PostgreSQL executes this recursively until no new rows are produced.

The final `SELECT * FROM org_tree ORDER BY depth, organization_name` returns the flat list
sorted breadth-first (all depth-0 roots first, then depth-1 children, etc.). This is
deliberately a **flat** representation — the UI uses `depthIndent(depth)` (see
`UI_CODE_EXPLANATIONS.md`) to visually indent nodes, rather than receiving nested JSON.

The recursive CTE uses a **leaner column set** than `_ORG_SELECT` (10 columns vs 36) — no
address fields, no contact/online-presence fields, no geographic LEFT JOINs, no parent name resolution — because the hierarchy
view shows only the organizational structure (name, type, status, depth), not full detail.
This maps to the dedicated `OrganizationHierarchyNodeResponse` schema (§2.10).

---

### 2.10 `api/schemas/organization.py`

**Requirement**

`api/routers/organization.py` needs 4 typed response models: one for each reference-data
catalogue (types, statuses), one for the full organization detail (36 fields including 8
JOINed context fields and 9 contact/online-presence fields), and one for the hierarchy tree's leaner node shape (10 fields).
Without this file the Organization router would have no `response_model=` to validate
against.

**Line-by-line**

Lines 1–9 — module docstring:

```python
"""
Pydantic response models for the Organization API (Tier 2).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""
```

Same audit-column exclusion and ConfigDict note as `schemas/bootstrap.py` and
`schemas/foundation.py`.

Lines 16–24 — `OrganizationTypeResponse` (6 fields):

Maps 1:1 to `nss.organization_type_master`: `organization_type_pk`, `organization_type_code`,
`organization_type_name`, `description` (nullable), `sort_order`, `is_active`.

Lines 27–35 — `OrganizationStatusResponse` (6 fields):

Maps 1:1 to `nss.organization_status_master`: `organization_status_pk`,
`organization_status_code`, `organization_status_name`, `description` (nullable),
`sort_order`, `is_active`.

Lines 38–86 — `OrganizationResponse` (36 fields):

The largest response model in the codebase. Field groups match the `_ORG_SELECT` column list:
- 4 core fields (`organization_pk`, `organization_id`, `organization_name`,
  `organization_code`).
- 3 classification fields from `organization_type_master` via JOIN.
- 3 lifecycle fields from `organization_status_master` via JOIN.
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
LEFT JOIN / nullable-FK reality.

Lines 89–107 — `OrganizationHierarchyNodeResponse` (10 fields):

The leaner shape used by the `/hierarchy` endpoint's recursive CTE. Includes `depth: int`
(computed by the CTE as `0` for roots, `depth + 1` for children) and the type/status
display names, but no address/geographic fields. The docstring explicitly notes "Children
are not nested — the tree is returned flat."

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
- **`docs/03_Solution/code_explanations/TIER0_SECURITY_AUDIT.md`** and
  **`TIER1_SECURITY_AUDIT.md`** — the security audit verdicts for the Bootstrap and Foundation
  API surfaces respectively. These are *not* retired by this document — they record findings and
  remediation status, which is a different concern from this document's per-file code narration,
  and continue to live alongside it in this same `code_explanations/` folder.
