"""
NSS ERP — Security middleware.

Adds protective HTTP headers to every response. These headers instruct
browsers to enforce security policies that mitigate common attack vectors.

Applied globally via app.middleware("http") in main.py.
"""

from starlette.requests import Request
from starlette.responses import Response


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
      Content-Security-Policy (CSP) — deferred until all inline styles
        are audited; Tailwind CSS is now pre-built (no CDN).
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    # Cache-Control: differentiate by path
    path = request.url.path
    if path.startswith("/api/"):
        # API responses must never be cached — always reflect current DB state
        response.headers["Cache-Control"] = "no-store"
    elif path.startswith("/assets/"):
        # Static assets (CSS, JS, images): cache for 1 day, revalidate after.
        # Cache-busted via ?v=N query strings on JS files; CSS rebuilt on deploy.
        response.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"

    return response
