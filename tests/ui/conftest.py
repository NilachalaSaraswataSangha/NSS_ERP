"""
NSS ERP — UI test fixtures (Playwright).

Provides browser, page, and authentication helpers for
end-to-end UI tests running against a live local server.

Requirements:
  - Local server running: python3 -m uvicorn api.main:app --port 8001
  - Local PostgreSQL running with nss schema bootstrapped
  - Playwright + Chromium installed:
      pip install pytest-playwright
      playwright install chromium

Usage:
  pytest tests/ui/                       # run all UI tests
  pytest tests/ui/ -m ui                 # explicit marker
  pytest tests/ui/ --headed              # watch the browser
  pytest tests/ui/ --slowmo 500          # slow down for debugging
"""

import pytest
from playwright.sync_api import Page, BrowserContext


# ── Configuration ──────────────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8001"

# Test credentials — must exist in the local DB.
# The bootstrap_admin.py script creates SS1 with NSSAdmin1 and
# force_password_change = TRUE. On first login the UI forces a
# password change. We change it to ADMIN_PASSWORD_NEW.
# On subsequent runs the password is already ADMIN_PASSWORD_NEW,
# so we try that first, falling back to the bootstrap default.
ADMIN_SS_ID = "SS1"
ADMIN_PASSWORD_BOOTSTRAP = "NSSAdmin1"
ADMIN_PASSWORD_NEW = "NSSTest@1"

# Currently only SS1 (admin) exists.
# Update when a separate member account is bootstrapped.
MEMBER_SS_ID = "SS1"


# ── Apply UI marker to all tests in this directory ─────────────────────

pytestmark = pytest.mark.ui


def pytest_collection_modifyitems(items):
    """Automatically add 'ui' marker to all tests in this package."""
    for item in items:
        if "/ui/" in str(item.fspath):
            item.add_marker(pytest.mark.ui)


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override default browser context settings."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def base_url():
    """Base URL for all page.goto() calls."""
    return BASE_URL


@pytest.fixture
def page(context: BrowserContext, base_url: str) -> Page:
    """
    Fresh page per test with base_url set.

    Each test gets a clean page (no cookies/storage from prior tests).
    """
    pg = context.new_page()
    pg.set_default_timeout(10000)  # 10s default timeout
    pg.set_default_navigation_timeout(15000)  # 15s for navigation
    yield pg
    pg.close()


# ── Login helpers ──────────────────────────────────────────────────────

def _do_login(page: Page, base_url: str, login_id: str, password: str):
    """
    Perform login via the login page, handling force_password_change.

    Flow:
      1. Navigate to /login, fill credentials, click Sign In.
      2. If force_password_change is active, the page stays on /login
         and shows the "Change Your Password" form. We fill in
         ADMIN_PASSWORD_NEW and submit.
      3. After success, wait for redirect to /dashboard.

    If the bootstrap password has already been changed (prior test run),
    the method tries ADMIN_PASSWORD_NEW first, falling back to the
    bootstrap default.
    """
    page.goto(f"{base_url}/login")
    page.wait_for_selector('[x-model="login_id"]', state="visible")

    # Try the post-change password first (works on subsequent runs)
    _attempt_login(page, login_id, password)

    # Wait a moment for the response to come back
    page.wait_for_timeout(1000)

    # Case 1: Already redirected to /dashboard — password was accepted,
    #         no force_password_change.
    if "/login" not in page.url:
        return

    # Case 2: Force password change form appeared
    change_form = page.locator('[x-model="newPassword"]')
    if change_form.is_visible():
        _handle_force_password_change(page)
        return

    # Case 3: Still on /login with an error — maybe wrong password.
    # If we used the new password, retry with the bootstrap default.
    error_el = page.locator('[x-text="error"]')
    if error_el.is_visible() and error_el.text_content():
        if password != ADMIN_PASSWORD_BOOTSTRAP:
            # Clear error state and retry with bootstrap password
            page.fill('[x-model="login_id"]', "")
            page.wait_for_timeout(200)
            page.fill('[x-model="login_id"]', login_id)
            page.fill('[x-model="password"]', ADMIN_PASSWORD_BOOTSTRAP)
            page.click("button:has-text('Sign In')")
            page.wait_for_timeout(1000)

            if "/login" not in page.url:
                return

            # Check for force password change after bootstrap login
            if change_form.is_visible():
                _handle_force_password_change(page)
                return

    # Final fallback: wait for redirect (might just be slow)
    page.wait_for_url(lambda url: "/login" not in url, timeout=10000)


def _attempt_login(page: Page, login_id: str, password: str):
    """Fill login form and click Sign In."""
    page.fill('[x-model="login_id"]', login_id)
    page.fill('[x-model="password"]', password)
    page.click("button:has-text('Sign In')")


def _handle_force_password_change(page: Page):
    """
    Handle the force_password_change form on the login page.

    Fills ADMIN_PASSWORD_NEW into both fields, clicks Change Password,
    and waits for redirect to /dashboard (1.5s delay built into the UI).
    """
    page.fill('[x-model="newPassword"]', ADMIN_PASSWORD_NEW)
    page.fill('[x-model="confirmPassword"]', ADMIN_PASSWORD_NEW)
    page.wait_for_timeout(300)
    page.click("button:has-text('Change Password')")

    # The UI shows "Password changed. Redirecting..." then waits 1.5s
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)


@pytest.fixture
def admin_page(context: BrowserContext, base_url: str) -> Page:
    """
    Page pre-authenticated as admin (SS1).

    Handles force_password_change on first run. On subsequent runs
    logs in directly with the changed password.
    Yields the page on /dashboard. Tests can navigate from there.
    """
    pg = context.new_page()
    pg.set_default_timeout(10000)
    pg.set_default_navigation_timeout(15000)
    _do_login(pg, base_url, ADMIN_SS_ID, ADMIN_PASSWORD_NEW)
    yield pg
    pg.close()


@pytest.fixture
def member_page(context: BrowserContext, base_url: str) -> Page:
    """
    Page pre-authenticated as a regular member.

    Currently uses SS1 (same as admin). Update MEMBER_SS_ID
    when a separate member account exists.
    """
    pg = context.new_page()
    pg.set_default_timeout(10000)
    pg.set_default_navigation_timeout(15000)
    _do_login(pg, base_url, MEMBER_SS_ID, ADMIN_PASSWORD_NEW)
    yield pg
    pg.close()


# ── Utility helpers ────────────────────────────────────────────────────

def wait_for_alpine(page: Page, timeout: int = 5000):
    """Wait until Alpine.js has initialized on the page."""
    page.wait_for_function(
        "() => typeof Alpine !== 'undefined' && Alpine.version !== undefined",
        timeout=timeout,
    )


def wait_for_toast(page: Page, text: str = None, timeout: int = 5000):
    """
    Wait for a toast/notification to appear.

    If text is provided, waits for a toast containing that text.
    """
    if text:
        page.wait_for_selector(f"text={text}", state="visible", timeout=timeout)
    else:
        # Generic toast — look for common toast containers
        page.wait_for_selector(
            ".toast, .notification, .alert-success, [x-show*='toast']",
            state="visible",
            timeout=timeout,
        )


def get_table_rows(page: Page, table_selector: str = ".admin-table tbody tr"):
    """Count visible table rows."""
    return page.locator(table_selector).count()


def click_nav_item(page: Page, tab_name: str):
    """Click a sidebar navigation item by its display text."""
    page.click(f".nav-item:has-text('{tab_name}')")
    page.wait_for_timeout(300)  # Allow Alpine.js reactivity
