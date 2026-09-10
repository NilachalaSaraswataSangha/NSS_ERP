# Security Layer — Per-File Code Explanations

| Field       | Value                                    |
|-------------|-------------------------------------------|
| Document    | SECURITY_CODE_EXPLANATIONS                |
| Version     | 1.0                                       |
| Scope       | `api/middleware.py` in full, plus the security-relevant portions of `api/config.py` and `api/main.py`, plus the SRI-pinned CDN assets in `frontend/` |
| Status      | Complete                                  |

---

## 1. Purpose of this document

This document is the authoritative, current reference for the **security-hardening layer**
cutting across Tier 0 and Tier 1: HTTP security headers, opt-in CORS, rate limiting, and
Subresource-Integrity-pinned CDN assets. It exists as its own dedicated document — separate from
`API_CODE_EXPLANATIONS.md` and `UI_CODE_EXPLANATIONS.md` — because security is a cross-cutting
concern that touches multiple files without owning any single one of them outright:
`api/middleware.py` is exclusively security code and is covered here in full; `api/config.py`
and `api/main.py` are primarily general application files (owned by
`API_CODE_EXPLANATIONS.md`), but each contains a specific, load-bearing security-relevant block
that this document walks through on its own so the full security posture can be read in one
place without cross-referencing two other documents' unrelated sections.

**How a request actually gets these protections — read this first if you're new to the
codebase.** Every single request to this app, whether it hits an API route or the static
frontend, passes through three independently-registered ASGI middleware layers before reaching
its destination, in this exact order (registration order in `api/main.py` — the first middleware
registered becomes the *outermost* layer):

```
Incoming HTTP request
        │
        ▼
1. Rate limiting (SlowAPIMiddleware, §2.3)
   — is this client IP over its 60/minute default? if so, short-circuit → HTTP 429
        │  (only requests under the limit proceed)
        ▼
2. CORS (CORSMiddleware, §2.3 — only present at all if CORS_ORIGINS is configured, §2.2)
   — is this a cross-origin request? if so, check it against the allow-list
        │
        ▼
3. Route handler runs (bootstrap.py / foundation.py / the frontend FileResponse — see
   API_CODE_EXPLANATIONS.md)
        │
        ▼
Response starts unwinding back out through the same three layers, in reverse —
security headers (add_security_headers, §2.1) are applied LAST, as the response leaves,
so every response gets them: successful ones, 429s, and CORS-rejected ones alike
        │
        ▼
Response reaches the client, now carrying X-Content-Type-Options / X-Frame-Options /
Referrer-Policy / Permissions-Policy (+ Cache-Control: no-store if it was an /api/* route)
```

This is why `add_security_headers` is registered *last* in `api/main.py` even though it's
conceptually the "outermost" protection a reader might expect first — ASGI middleware wraps in
registration order, so the last one registered is the *innermost* on the way in but, because
every response must unwind back out through it, still the one every response carries on the way
out. If this ordering is ever changed, `tests/test_security.py` (see
`TESTING_CODE_EXPLANATIONS.md`) is what would catch a regression — none of the functional tests
in `test_bootstrap.py`/`test_foundation.py` check headers or throttling at all.

**Relationship to other documents:**
- `api/middleware.py` has no other home — its full **Requirement**/**Line-by-line** entry lives
  here, not in `API_CODE_EXPLANATIONS.md`.
- `api/config.py`'s `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`API_PORT` settings are
  explained in `API_CODE_EXPLANATIONS.md` §2.1; only its security-relevant settings
  (`CORS_ORIGINS`, `RATE_LIMIT`, `DISABLE_DOCS`) are walked through here.
- `api/main.py`'s router registration, lifespan handler, and frontend-serving routes are
  explained in `API_CODE_EXPLANATIONS.md` §2.3; only its middleware-registration block is walked
  through here.
- `frontend/index.html` and `frontend/foundation.html`'s CDN `<head>` tags are explained in full
  in `UI_CODE_EXPLANATIONS.md`; this document summarizes just the security rationale for the
  pinning and points there for the literal markup.
- `tests/test_security.py` — the test file that verifies everything in this document — is
  explained in `TESTING_CODE_EXPLANATIONS.md`, not here.
- `TIER0_SECURITY_AUDIT.md` and `TIER1_SECURITY_AUDIT.md` (same folder) record the audit
  *verdicts* (what was checked, pass/fail/advisory) — a different concern from this document's
  code-level *narration* of how the protections are implemented.

---

## 2. Files

### 2.1 `api/middleware.py`

**Requirement**

Every HTTP response — API or static frontend — should carry a baseline set of protective headers
(anti-clickjacking, anti-MIME-sniffing, referrer control, denied device APIs) and API responses
specifically must never be cached, since they reflect live database state. FastAPI has no
built-in "always add these headers" primitive beyond ASGI middleware, so this file supplies that
middleware as a single reusable function. Without it, none of the routers would need to change,
but every response leaving the app would lack `X-Frame-Options`, `X-Content-Type-Options`, etc.,
and a browser or intermediate cache could serve a stale `/api/*` response.

**Line-by-line**

```python
"""
NSS ERP — Security middleware.

Adds protective HTTP headers to every response. These headers instruct
browsers to enforce security policies that mitigate common attack vectors.

Applied globally via app.middleware("http") in main.py.
"""
```

The module docstring states the file "adds protective HTTP headers to every response," that
these headers "instruct browsers to enforce security policies," and that the middleware is
applied globally via `app.middleware("http")` in `main.py`.

```python
from starlette.requests import Request
from starlette.responses import Response
```

Both are imported from Starlette directly, not FastAPI's re-export, because ASGI HTTP middleware
operates at the Starlette layer FastAPI is built on. `Response` is used only as the return-type
annotation below.

```python
async def add_security_headers(request: Request, call_next) -> Response:
```

The middleware function signature FastAPI/Starlette expects: it receives the incoming `request`
and a `call_next` callable that invokes the rest of the middleware chain plus the route handler.

```python
    """
    Inject security headers into every HTTP response.

    Headers added to ALL responses:
      X-Content-Type-Options: nosniff
        Prevents browsers from MIME-sniffing the response away from
        the declared Content-Type (mitigates drive-by download attacks).

      X-Frame-Options: DENY
        Prevents the page from being embedded in an iframe anywhere
        (mitigates clickjacking).

      Referrer-Policy: strict-origin-when-cross-origin
        Sends only the origin (not full URL) on cross-origin requests.
        Prevents leaking internal URL paths.

      Permissions-Policy: camera=(), microphone=(), geolocation=()
        Denies access to device APIs the app doesn't use.

    Headers added to API responses only (/api/* paths):
      Cache-Control: no-store
        Prevents caching of API responses so they always reflect
        current database state. NOT applied to static assets
        (HTML, CSS, JS, images) — browsers should cache those normally.

    Not added here:
      X-XSS-Protection — obsolete in modern browsers; superseded by CSP.
      Strict-Transport-Security (HSTS) — Render adds this automatically
        on custom domains with TLS.
      Content-Security-Policy (CSP) — deferred until the frontend CDN
        strategy is finalized (Tailwind Play CDN uses inline styles).
    """
```

This extended docstring enumerates exactly which headers are added unconditionally
(`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`), which is
added conditionally (`Cache-Control: no-store`, API routes only), and which headers were
deliberately *not* added and why: `X-XSS-Protection` (obsolete, superseded by CSP),
`Strict-Transport-Security` (Render adds this automatically on custom domains with TLS — setting
it here without controlling TLS termination would be misleading), and `Content-Security-Policy`
(deferred — the Tailwind Play CDN injects inline `<style>` tags at runtime, and a strict CSP
would break the UI before the CDN strategy is finalized).

```python
    response = await call_next(request)
```

Runs the rest of the middleware chain and the endpoint handler to completion; headers are added
**on the way out** (to the response), not on the way in.

```python
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
```

`X-Content-Type-Options: nosniff` stops the browser from MIME-sniffing the response body against
its declared `Content-Type`, closing off drive-by download attacks where a mislabeled file type
gets executed.

`X-Frame-Options: DENY` refuses to let the page be embedded in an `<iframe>` on any domain,
including the same origin, since this app has no legitimate framing use case (API + a
verification UI).

`Referrer-Policy: strict-origin-when-cross-origin` means cross-origin navigations away from this
app send only the origin (not the full path/query) as the referrer; same-origin navigations still
send the full URL. Prevents leaking internal API paths to third-party analytics or CDNs.

`Permissions-Policy: camera=(), microphone=(), geolocation=()` denies every origin (including the
page itself) access to the camera, microphone, and geolocation device APIs, none of which this
ERP app has any use for.

```python
    # Cache-Control: no-store only on API responses, not static assets
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
```

Scoped exclusively to `/api/*` paths. API responses must always reflect the current database
state, so caching is forbidden. This is deliberately **not** applied to `/`, `/assets/*`, or
`/foundation` — those are static HTML/CSS/JS/images that should be cached normally by the
browser; forcing `no-store` on them would mean re-downloading the whole frontend on every page
load for no security benefit.

```python
    return response
```

Hands the (now header-decorated) response back up the middleware chain.

---

### 2.2 `api/config.py` — security-relevant settings

*(The rest of this file — `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`API_PORT` and
the `validate()`/singleton machinery — is explained in full in `API_CODE_EXPLANATIONS.md` §2.1.
Only the three security-relevant settings are covered here.)*

**Requirement**

The security middleware in `api/main.py` needs three independently-tunable knobs — whether docs
are exposed, which origins (if any) may make cross-origin requests, and how aggressively to rate
limit — sourced from the environment so the same codebase can run permissively in local
development and restrictively in production without a code change. Without these three settings
existing on the `Settings` object, `api/main.py` would have to hardcode a rate limit, hardcode
CORS behavior (on or off, with no per-environment origin list), and hardcode whether `/docs` is
reachable — none of which is safe to bake into source for a public deployment.

**Line-by-line**

```python
DISABLE_DOCS: bool = os.environ.get("DISABLE_DOCS", "").lower() in ("1", "true", "yes")
```

Reads the raw string, lowercases it, and checks membership in a small set of truthy spellings.
Anything else (including an unset variable, which reads as `""`) evaluates to `False`, so docs
are enabled by default — deliberately permissive locally, meant to be flipped to `true` in the
production environment (e.g. Render's dashboard).

```python
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "").split(",")
    if o.strip()
]
```

A list comprehension that splits the `CORS_ORIGINS` env var on commas, strips whitespace from
each entry, and drops empty strings. An unset `CORS_ORIGINS` produces `[]` (empty list) — this is
the "CORS inactive" sentinel that `api/main.py` checks with `if settings.CORS_ORIGINS:`. There is
no wildcard/`"*"` shorthand supported — every allowed origin must be listed explicitly, by
design.

```python
RATE_LIMIT: str = os.environ.get("RATE_LIMIT", "60/minute")
```

A rate-limit string in the `limits` library's `<count>/<period>` syntax, consumed directly by
`slowapi.Limiter`'s `default_limits` argument in `api/main.py`. A safe, permissive default that
still bounds abuse even if the operator never sets this variable.

---

### 2.3 `api/main.py` — security middleware registration

*(The rest of this file — the FastAPI app construction, lifespan handler, router registration,
and frontend-serving routes — is explained in full in `API_CODE_EXPLANATIONS.md` §2.3. Only the
middleware-registration block is covered here.)*

**Requirement**

Three independent protections (rate limiting, CORS, security headers) each need to be registered
as ASGI middleware in a specific order for the security guarantees to actually hold — e.g.
security headers must wrap the *entire* chain so even a 429 (rate-limited) or CORS-preflight
response still carries them. This block is the one place in the codebase where that ordering is
decided and enforced; getting it wrong (as happened once during development — see below) silently
disables a protection without any functional test catching it.

**Line-by-line**

```python
from fastapi.middleware.cors import CORSMiddleware
```

FastAPI's built-in CORS middleware.

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
```

The rate-limiting engine (`Limiter`), the exception type it raises on breach, the ASGI middleware
that actually enforces limits on every request, and the key function that identifies a client by
IP address.

```python
from api.middleware import add_security_headers
```

The function from §2.1 above.

```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
)
```

A module-level `Limiter` instance keyed by client IP, with the default rate (e.g. `"60/minute"`)
taken from configuration. This same `limiter` object is imported directly by
`tests/test_security.py` to call `limiter.reset()` between tests.

```python
# 1. Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

Registered first, so it becomes the **outermost** middleware, running first on the way in and
last on the way out. `app.state.limiter = limiter` makes the limiter reachable from
`SlowAPIMiddleware` via the request's `app` reference; `app.add_exception_handler(...)` converts
a `RateLimitExceeded` exception into an HTTP 429 response with a `Retry-After` header;
`app.add_middleware(SlowAPIMiddleware)` is the actual enforcement — **without this call the
limiter is configured but never consulted on incoming requests**. This exact omission happened
during development and was caught only because `test_rate_limit_returns_429` exists — a
functional test would never have noticed, since every request would still have succeeded, just
without a limit.

```python
# 2. CORS — only add if origins are configured
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
```

CORS middleware is added **only if** at least one origin is configured; with the default empty
list, it's never added at all, so cross-origin requests get no CORS headers regardless of what
`Origin` header they send (verified by `tests/test_security.py::TestCORS`). `allow_methods=
["GET"]` matches the read-only nature of every current endpoint; `allow_origins` is never set to
`"*"` — a real allow-list or nothing.

```python
# 3. Security headers on every response
app.middleware("http")(add_security_headers)
```

Registered last, so it becomes the **innermost** middleware relative to the two above, but since
headers are set on the response as it unwinds back *out* through every layer, it still decorates
every response including 429s and CORS preflights. This call registers the function from
`api/middleware.py` as HTTP middleware, using function-call syntax (rather than the
`@app.middleware("http")` decorator form) because the function is defined in a separate module.

**Net effective order** (per the file's own comments): the request path is Security Headers →
CORS → Rate Limiting → endpoint, and the response path unwinds in reverse, so security headers
are the last thing applied to every outgoing response no matter which layer generated it.

---

### 2.4 CDN Subresource Integrity (SRI) pinning — `frontend/index.html`, `frontend/foundation.html`

*(The rest of both files' markup — body structure, Alpine.js directives, every card/tab — is
explained in full in `UI_CODE_EXPLANATIONS.md` §2.1 and §2.3. This entry covers only the `<head>`
CDN block, which is byte-for-byte identical in both files.)*

**Requirement**

Every third-party script/stylesheet loaded from a CDN is a supply-chain trust boundary — if the
CDN is compromised or serves a tampered file, the browser has no way to know unless the page
tells it what hash to expect. Two of the three CDN dependencies (DaisyUI, Alpine.js) can be
pinned to an exact version with a Subresource Integrity hash; the third (Tailwind's Play CDN)
cannot, because it's a browser-side JIT compiler that generates CSS dynamically from the page's
own class names — there is no single static file whose hash could be checked. Before this
hardening pass, DaisyUI and Alpine.js were both loaded unpinned (`@4`, `@3` — "latest of major
version"), so a compromised or yanked CDN release could silently change what code the browser
executes on every page load; pinning removes that window entirely.

**Line-by-line** (identical in `frontend/index.html` and `frontend/foundation.html`'s `<head>`
block):

```html
<!-- Tailwind CSS Play CDN (Tailwind 3.x JIT — generates utility classes in-browser) -->
<script src="https://cdn.tailwindcss.com"></script>
```

The comment documents inline why no SRI hash follows. The `<script>` tag itself carries no
`integrity`/`crossorigin` attributes at all — this is the one CDN dependency that cannot be
pinned: the script itself is a JIT compiler that scans the page's HTML for Tailwind utility class
names and generates matching CSS rules in the browser at runtime. The actual *styling* differs
per page depending on which classes appear, so there is no single fixed file whose bytes could be
hashed once and checked forever.

```html
<!-- DaisyUI 4.12.14 (requires Tailwind 3.x) -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css" rel="stylesheet" integrity="sha384-iMbeRReqpIEp0z+cPe0FZxnbV/GbGyGjDfou8Rjcr6KSJIptc245QXNVjLMtu5TR" crossorigin="anonymous">
```

The comment records the exact pinned version for anyone reading the source. `@4.12.14` in the URL
pins the exact npm release (not `@4`, which would silently track the newest 4.x release on every
page load); `integrity="sha384-..."` is the base64-encoded SHA-384 hash of the exact file jsDelivr
is expected to serve; `crossorigin="anonymous"` is required by the browser's SRI spec for any
cross-origin resource carrying an `integrity` attribute — without it, the browser refuses to even
attempt the integrity check. If jsDelivr ever served different bytes at this exact URL
(compromise, or a broken deploy), the browser would refuse to apply the stylesheet at all — a
broken (unstyled) page, not a silently compromised one.

```html
<!-- Alpine.js 3.14.8 -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js" integrity="sha384-X9kJyAubVxnP0hcA+AMMs21U445qsnqhnUF8EBlEpP3a42Kh/JwWjlv2ZcvGfphb" crossorigin="anonymous"></script>
```

Same pinning/SRI/`crossorigin` pattern as DaisyUI, applied to the Alpine.js runtime itself (the
library every `x-data`/`x-init`/`x-text` directive in both pages depends on); `defer` ensures the
script executes only after the HTML is fully parsed, so every `x-data` element it needs to bind
to already exists in the DOM.

**What was removed to get here:** an older, unpinned `tailwindcss@2` prebuilt CSS `<link>` (the
pre-JIT Tailwind 2.x distribution) and a separate, incompatible attempt at `@tailwindcss/browser`
4.x (which conflicts with DaisyUI 4.x's Tailwind-3.x-only compatibility) were both deleted from
both HTML files as part of this same pass — see `UI_CODE_EXPLANATIONS.md` for the current full
`<head>` block in context.

---

## 3. Cross-references

- **`docs/03_Solution/architecture/code_explanations/API_CODE_EXPLANATIONS.md`** — the full
  file-by-file walkthrough of `api/config.py` and `api/main.py`, of which this document covers
  only the security-relevant slices.
- **`docs/03_Solution/architecture/code_explanations/UI_CODE_EXPLANATIONS.md`** — the full
  markup-level walkthrough of `frontend/index.html` and `frontend/foundation.html`, including
  every CDN `<script>`/`<link>` tag this document only summarizes.
- **`docs/03_Solution/architecture/code_explanations/TESTING_CODE_EXPLANATIONS.md`** —
  `tests/test_security.py`'s per-test walkthrough; that file is the executable verification of
  everything documented here.
- **`docs/03_Solution/architecture/code_explanations/TIER0_SECURITY_AUDIT.md`** and
  **`TIER1_SECURITY_AUDIT.md`** — the audit verdicts (pass/fail/advisory status) for the Bootstrap
  and Foundation API surfaces, a different concern from this document's code-level narration.
