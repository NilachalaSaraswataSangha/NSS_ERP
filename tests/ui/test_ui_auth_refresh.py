"""
UI tests for the shared auth layer (auth.js).

`NSSAuth.apiFetch()` is the single door every authenticated request goes
through, and its refresh logic had no coverage at all: only logout was tested.
Two failure modes matter here — a request that silently 401s instead of
refreshing (the user sees an empty panel), and a refresh loop that never gives
up (the user is stuck on a page that will not load).

Most of these drive the real functions with `window.fetch` stubbed, so the
scripted 401-then-refresh sequences are deterministic. One test at the end plants
a genuinely expired access token and lets the real API refresh it, which is the
only way to prove the wire format of `/api/v1/auth/refresh` still matches what
auth.js sends.

Requires a live server (BASE_URL http://127.0.0.1:8001). Run with:
    python3 -m pytest tests/ui/test_ui_auth_refresh.py
"""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.ui


# Mint a decodable JWT whose exp is `offset` seconds from now. auth.js only
# peeks at the payload (decodePayload), so the signature is irrelevant.
_MAKE_TOKEN = """
(offset) => {
    const b64 = (o) => btoa(JSON.stringify(o)).replace(/=+$/, '');
    return b64({ alg: 'HS256', typ: 'JWT' }) + '.' +
           b64({ sub: 'SS1', exp: Math.floor(Date.now() / 1000) + offset }) + '.sig';
}
"""

# Installs a scripted fetch stub, runs apiFetch, and returns what happened.
# `script` is a list of {status, body} consumed in call order; any request to
# /auth/refresh is answered from `refresh` instead.
_RUN_API_FETCH = """
async ({ accessToken, refreshToken, script, refresh }) => {
    localStorage.clear();
    if (accessToken) localStorage.setItem('nss_access_token', accessToken);
    if (refreshToken) localStorage.setItem('nss_refresh_token', refreshToken);

    const calls = [];
    let i = 0;
    const realFetch = window.fetch;
    window.fetch = (url, opts = {}) => {
        calls.push({
            url: String(url),
            authorization: (opts.headers || {}).Authorization || null,
            contentType: (opts.headers || {})['Content-Type'] || null,
            cache: opts.cache || null,
            method: opts.method || 'GET',
        });
        if (String(url).includes('/auth/refresh')) {
            return Promise.resolve({
                ok: refresh.ok,
                status: refresh.ok ? 200 : 401,
                json: () => Promise.resolve({ access_token: refresh.token }),
            });
        }
        const step = script[Math.min(i++, script.length - 1)];
        return Promise.resolve({
            ok: step.status < 400,
            status: step.status,
            json: () => Promise.resolve(step.body || {}),
        });
    };

    // logout() navigates to /login, which would tear the page down mid-test.
    let loggedOut = false;
    const realLogout = NSSAuth.logout;
    NSSAuth.logout = () => { loggedOut = true; NSSAuth.clearTokens(); };

    let status = null, error = null;
    try {
        const res = await NSSAuth.apiFetch('/api/v1/admin/users');
        status = res.status;
    } catch (e) {
        error = e.message;
    }

    window.fetch = realFetch;
    NSSAuth.logout = realLogout;
    const stored = localStorage.getItem('nss_access_token');
    localStorage.clear();
    return { calls, status, error, loggedOut, storedToken: stored };
}
"""


@pytest.fixture
def auth_page(page: Page, base_url):
    """login.html loads auth.js and needs no session."""
    page.goto(f"{base_url}/login")
    page.wait_for_function("() => typeof NSSAuth !== 'undefined'", timeout=10_000)
    return page


def _token(page, offset_seconds):
    return page.evaluate(_MAKE_TOKEN, offset_seconds)


def _run(page, access_offset=3600, refresh_token="refresh-token",
         script=None, refresh_ok=True, refresh_offset=3600, access_token=...):
    if access_token is ...:
        access_token = _token(page, access_offset) if access_offset is not None else None
    return page.evaluate(_RUN_API_FETCH, {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "script": script or [{"status": 200, "body": {"ok": True}}],
        "refresh": {"ok": refresh_ok, "token": _token(page, refresh_offset)},
    })


# ── Token expiry maths ──────────────────────────────────────────────────────


class TestTokenExpiry:

    @pytest.mark.parametrize("offset,expected", [
        (3600, False),   # comfortably valid
        (-10, True),     # already expired
        (15, True),      # inside the 30s pre-expiry buffer
        (45, False),     # outside the buffer
    ])
    def test_is_token_expired_applies_a_30s_buffer(self, auth_page, offset, expected):
        """
        The buffer exists so a token cannot expire in flight. Getting its sign
        wrong either refreshes on every call or serves a request that 401s.
        """
        token = _token(auth_page, offset)
        assert auth_page.evaluate("(t) => NSSAuth.isTokenExpired(t)", token) is expected

    @pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c"])
    def test_undecodable_token_counts_as_expired(self, auth_page, token):
        """Fail closed: an unreadable token must not be sent as a credential."""
        assert auth_page.evaluate("(t) => NSSAuth.isTokenExpired(t)", token) is True


# ── apiFetch: refresh before the call ───────────────────────────────────────


class TestApiFetchPreRefresh:

    def test_valid_token_is_used_without_refreshing(self, auth_page):
        res = _run(auth_page)
        assert res["status"] == 200
        assert [c["url"] for c in res["calls"]] == ["/api/v1/admin/users"], res["calls"]
        assert res["calls"][0]["authorization"].startswith("Bearer ")
        assert res["calls"][0]["cache"] == "no-store", (
            "authenticated, scope-filtered data must never be served from cache"
        )

    def test_expired_token_is_refreshed_before_the_request(self, auth_page):
        res = _run(auth_page, access_offset=-60)
        urls = [c["url"] for c in res["calls"]]
        assert urls == ["/api/v1/auth/refresh", "/api/v1/admin/users"], urls
        assert res["status"] == 200
        assert res["loggedOut"] is False
        # The retried request must carry the NEW token, not the expired one.
        assert res["calls"][1]["authorization"] == f"Bearer {res['storedToken']}"

    def test_expired_token_with_no_refresh_token_logs_out(self, auth_page):
        res = _run(auth_page, access_offset=-60, refresh_token=None)
        assert res["loggedOut"] is True
        assert res["error"] == "Session expired. Please log in again."
        assert [c["url"] for c in res["calls"]] == [], (
            "no request should be attempted once the session is unrecoverable"
        )

    def test_failed_refresh_clears_tokens_and_raises(self, auth_page):
        res = _run(auth_page, access_offset=-60, refresh_ok=False)
        assert res["loggedOut"] is True
        assert res["error"] == "Session expired. Please log in again."
        assert res["storedToken"] is None, "a rejected refresh must clear the tokens"


# ── apiFetch: 401 mid-flight ────────────────────────────────────────────────


class TestApiFetch401:

    def test_401_triggers_one_refresh_and_one_retry(self, auth_page):
        """
        A token can be valid by the clock and still rejected (revoked account,
        server restart). One refresh cycle, one retry — no more.
        """
        res = _run(auth_page, script=[
            {"status": 401}, {"status": 200, "body": {"ok": True}},
        ])
        urls = [c["url"] for c in res["calls"]]
        assert urls == [
            "/api/v1/admin/users", "/api/v1/auth/refresh", "/api/v1/admin/users",
        ], urls
        assert res["status"] == 200
        assert res["calls"][2]["authorization"] == f"Bearer {res['storedToken']}"

    def test_repeated_401_is_not_retried_forever(self, auth_page):
        """
        The retry is deliberately not recursive: a second 401 is returned to the
        caller rather than starting another refresh cycle.
        """
        res = _run(auth_page, script=[{"status": 401}])
        urls = [c["url"] for c in res["calls"]]
        assert urls.count("/api/v1/auth/refresh") == 1, urls
        assert urls.count("/api/v1/admin/users") == 2, urls
        assert res["status"] == 401
        assert res["loggedOut"] is False

    def test_401_with_unusable_refresh_token_logs_out(self, auth_page):
        res = _run(auth_page, script=[{"status": 401}], refresh_ok=False)
        assert res["loggedOut"] is True
        assert res["error"] == "Session expired. Please log in again."

    def test_json_body_gets_a_content_type(self, auth_page):
        """apiFetch defaults Content-Type for string bodies so callers need not."""
        res = auth_page.evaluate("""async (token) => {
            localStorage.setItem('nss_access_token', token);
            const calls = [];
            const realFetch = window.fetch;
            window.fetch = (url, opts = {}) => {
                calls.push((opts.headers || {})['Content-Type'] || null);
                return Promise.resolve({ ok: true, status: 200,
                                        json: () => Promise.resolve({}) });
            };
            await NSSAuth.apiFetch('/api/v1/x', { method: 'POST', body: '{"a":1}' });
            window.fetch = realFetch;
            localStorage.clear();
            return calls;
        }""", _token(auth_page, 3600))
        assert res == ["application/json"], res


# ── initAuth: a failed /auth/me is not always a dead session ───────────────


# Drives NSSLayout.initAuth with a scripted apiFetch. `redirectUrl` is a hash on
# the current page, so the endSession path is observable (location.hash) without
# the page actually navigating away mid-evaluate.
_RUN_INIT_AUTH = """
async ({ script, cached, hasToken }) => {
    localStorage.clear();
    if (hasToken) {
        const b64 = (o) => btoa(JSON.stringify(o)).replace(/=+$/, '');
        localStorage.setItem('nss_access_token',
            b64({ alg: 'HS256', typ: 'JWT' }) + '.' +
            b64({ sub: 'SS1', exp: Math.floor(Date.now() / 1000) + 3600 }) + '.sig');
    }
    if (cached) localStorage.setItem('nss_user', JSON.stringify(cached));

    let i = 0;
    const calls = [];
    const realApiFetch = NSSAuth.apiFetch;
    NSSAuth.apiFetch = (url) => {
        calls.push(url);
        const step = script[Math.min(i++, script.length - 1)];
        if (step.throws) return Promise.reject(new Error('network down'));
        return Promise.resolve({
            ok: step.status < 400,
            status: step.status,
            headers: { get: (h) => h === 'Retry-After' ? '0' : null },
            json: () => Promise.resolve(step.body || {}),
        });
    };

    location.hash = '';
    const component = { ...NSSLayout.mixin() };
    let returned = null;
    try {
        returned = await NSSLayout.initAuth(component, { redirectUrl: '#ended' });
    } finally {
        NSSAuth.apiFetch = realApiFetch;
    }
    const out = {
        calls,
        returned,
        currentUser: component.currentUser,
        authWarning: component.authWarning || null,
        authLoading: component.authLoading,
        tokenKept: !!localStorage.getItem('nss_access_token'),
        endedSession: location.hash === '#ended',
    };
    localStorage.clear();
    location.hash = '';
    return out;
}
"""

_CACHED_USER = {"person_name": "Test User", "sangha_sevi_id": "SS1", "scopes": []}


@pytest.fixture
def layout_page(page: Page, base_url):
    """
    login.html does not load nss-layout.js (it has no sidebar), so inject it.
    Deliberately unauthenticated: initAuth is driven with a stubbed apiFetch,
    which keeps these deterministic and costs the server nothing.
    """
    page.goto(f"{base_url}/login")
    page.add_script_tag(url="/assets/js/nss-layout.js")
    page.wait_for_function("() => typeof NSSLayout !== 'undefined'", timeout=15_000)
    return page


def _init_auth(page, script, cached=..., has_token=True):
    return page.evaluate(_RUN_INIT_AUTH, {
        "script": script,
        "cached": _CACHED_USER if cached is ... else cached,
        "hasToken": has_token,
    })


class TestInitAuthFailureHandling:
    """
    The regression: initAuth treated every non-ok /auth/me as an invalid
    session — it cleared the tokens and redirected to /login. The API rate
    limits at 60 requests/minute per IP by default, so a burst of tab switches
    was enough to log a working session out. Only 401/403 may end a session.
    """

    def test_ok_response_populates_and_caches_the_user(self, layout_page):
        res = _init_auth(layout_page, [{"status": 200, "body": {"person_name": "A"}}])
        assert res["returned"] is True
        assert res["currentUser"]["person_name"] == "A"
        assert res["endedSession"] is False
        assert res["authWarning"] is None
        assert res["authLoading"] is False

    def test_rate_limited_then_ok_is_retried_once(self, layout_page):
        res = _init_auth(layout_page, [
            {"status": 429}, {"status": 200, "body": {"person_name": "A"}},
        ])
        assert res["calls"] == ["/api/v1/auth/me", "/api/v1/auth/me"], res["calls"]
        assert res["currentUser"]["person_name"] == "A"
        assert res["endedSession"] is False
        assert res["tokenKept"] is True

    def test_persistent_rate_limit_keeps_the_session(self, layout_page):
        """
        Two 429s in a row: still not an auth failure. Render from the cached
        profile, keep the tokens, warn — do not log the user out.
        """
        res = _init_auth(layout_page, [{"status": 429}])
        assert res["endedSession"] is False, (
            "a rate-limited profile load must not end the session"
        )
        assert res["tokenKept"] is True
        assert res["currentUser"]["sangha_sevi_id"] == "SS1"
        assert res["authWarning"], "the stale profile should be flagged to the user"
        assert res["calls"] == ["/api/v1/auth/me", "/api/v1/auth/me"], res["calls"]

    def test_server_error_keeps_the_session(self, layout_page):
        res = _init_auth(layout_page, [{"status": 503}])
        assert res["endedSession"] is False
        assert res["tokenKept"] is True
        assert res["currentUser"]["sangha_sevi_id"] == "SS1"
        # A 5xx is not retried — one attempt, then fall back.
        assert res["calls"] == ["/api/v1/auth/me"], res["calls"]

    def test_network_failure_keeps_the_session(self, layout_page):
        res = _init_auth(layout_page, [{"throws": True}])
        assert res["endedSession"] is False
        assert res["tokenKept"] is True
        assert res["currentUser"]["sangha_sevi_id"] == "SS1"

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_refusal_ends_the_session(self, layout_page, status):
        """The one case that must still clear tokens and redirect."""
        res = _init_auth(layout_page, [{"status": status}])
        assert res["endedSession"] is True, f"{status} should end the session"
        assert res["tokenKept"] is False
        assert res["returned"] is False

    def test_transient_failure_with_no_cached_profile_ends_the_session(
        self, layout_page
    ):
        """
        Without a cached profile there is nothing to render, so falling through
        would leave a blank shell. Ending the session is the honest outcome.
        """
        res = _init_auth(layout_page, [{"status": 503}], cached=None)
        assert res["endedSession"] is True
        assert res["currentUser"] is None

    # NB: the "no access token at all" path is deliberately not exercised here.
    # It goes through NSSAuth.requireAuth(), which assigns
    # window.location.href = "/login" — a real navigation that would tear down
    # the page mid-evaluate. It is covered by the logout/guard tests instead.


# ── The real refresh endpoint ───────────────────────────────────────────────


@pytest.mark.integration
def test_expired_session_recovers_against_the_live_api(admin_page: Page, base_url):
    """
    End-to-end proof that auth.js and /api/v1/auth/refresh still agree on the
    wire format: plant an expired access token on a real session and let
    apiFetch recover it. Skips if the login flow stored no refresh token.
    """
    admin_page.goto(f"{base_url}/admin")
    admin_page.wait_for_function("() => typeof NSSAuth !== 'undefined'", timeout=10_000)

    if not admin_page.evaluate("() => localStorage.getItem('nss_refresh_token')"):
        pytest.skip("login did not store a refresh token in this build")

    expired = admin_page.evaluate(_MAKE_TOKEN, -120)
    result = admin_page.evaluate("""async (expired) => {
        const good = localStorage.getItem('nss_access_token');
        localStorage.setItem('nss_access_token', expired);
        try {
            const res = await NSSAuth.apiFetch('/api/v1/auth/me');
            return { status: res.status,
                     rotated: localStorage.getItem('nss_access_token') !== expired };
        } catch (e) {
            return { error: e.message };
        } finally {
            if (localStorage.getItem('nss_access_token') === expired) {
                localStorage.setItem('nss_access_token', good);
            }
        }
    }""", expired)

    assert result.get("error") is None, result
    assert result["status"] == 200, result
    assert result["rotated"] is True, (
        "the expired access token was not replaced by a refreshed one"
    )
