"""
NSS ERP — Security middleware.

Adds protective HTTP headers to every response. These headers instruct
browsers to enforce security policies that mitigate common attack vectors.

Applied globally via app.middleware("http") in main.py.
"""

from starlette.requests import Request
from starlette.responses import Response

from api.config import settings

# Paths exempt from CSP: FastAPI's generated Swagger UI / ReDoc pages embed an
# inline <script> block and load their bundles from a CDN, so enforcing the
# app policy would break them. They are disabled entirely in production via
# DISABLE_DOCS, so exempting them costs nothing there.
CSP_EXEMPT_PATHS: tuple[str, ...] = ("/docs", "/redoc", "/openapi.json")

# The single external origin the frontend actually loads: Alpine.js is served
# from jsDelivr with an SRI integrity hash on every page.
_ALPINE_CDN = "https://cdn.jsdelivr.net"


def build_csp() -> str:
    """
    Assemble the Content-Security-Policy value from verified frontend usage.

    Every allowance below is present because the frontend provably needs it —
    not defensively. Recorded as advisory A2 in
    docs/03_Solution/security/TIER5_SECURITY_AUDIT.md.

      script-src 'unsafe-eval'
        Alpine.js 3's default build compiles directive expressions
        (x-data, x-show, @click) with new Function(). Removing this needs
        the @alpinejs/csp build plus rewriting every inline expression as a
        named method — tracked as a follow-up, not a Tier 5 change.
        'unsafe-inline' is deliberately NOT granted: all inline event
        handlers were removed so injected on*= attributes cannot execute.

      style-src 'unsafe-inline'
        The pages style extensively via inline style= attributes and one
        inline <style> block. Nonces cannot cover style attributes, so this
        can only be tightened by migrating those attributes to classes.

      img-src data:
        tailwind.min.css embeds form-control icons as data:image/svg+xml.

    Not granted at all: object-src (no plugins), frame-ancestors (no framing,
    matching X-Frame-Options: DENY), and connect-src beyond 'self' — every
    fetch in the frontend is a same-origin relative /api/... call.
    """
    script_src = ["'self'", "'unsafe-eval'", _ALPINE_CDN, *settings.CSP_SCRIPT_SRC_EXTRA]
    style_src = ["'self'", "'unsafe-inline'", *settings.CSP_STYLE_SRC_EXTRA]

    directives = [
        "default-src 'self'",
        f"script-src {' '.join(script_src)}",
        f"style-src {' '.join(style_src)}",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    return "; ".join(directives)


async def add_security_headers(request: Request, call_next) -> Response:
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

      Content-Security-Policy
        See build_csp(). Emitted as Content-Security-Policy-Report-Only
        when CSP_REPORT_ONLY is set, so a tightened policy can be trialled
        against a live deployment before it starts blocking. Suppressed
        entirely by CSP_ENABLED=false, and skipped for CSP_EXEMPT_PATHS.

    Headers added to API responses only (/api/* paths):
      Cache-Control: no-store
        Prevents caching of API responses so they always reflect
        current database state.

    Headers added to static asset responses (/assets/* paths):
      Cache-Control: public, max-age=86400, must-revalidate
        Caches static files for 24 hours. JS files use ?v=N cache
        busting; CSS is rebuilt on deploy. Images rarely change.

    Not added here:
      X-XSS-Protection — obsolete in modern browsers; superseded by CSP.
      Strict-Transport-Security (HSTS) — Render adds this automatically
        on custom domains with TLS.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    path = request.url.path

    # Content-Security-Policy
    if settings.CSP_ENABLED and not path.startswith(CSP_EXEMPT_PATHS):
        header = (
            "Content-Security-Policy-Report-Only"
            if settings.CSP_REPORT_ONLY
            else "Content-Security-Policy"
        )
        response.headers[header] = build_csp()

    # Cache-Control: differentiate by path
    if path.startswith("/api/"):
        # API responses must never be cached — always reflect current DB state
        response.headers["Cache-Control"] = "no-store"
    elif path.startswith("/assets/"):
        # Static assets (CSS, JS, images): cache for 1 day, revalidate after.
        # Cache-busted via ?v=N query strings on JS files; CSS rebuilt on deploy.
        response.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"

    return response
