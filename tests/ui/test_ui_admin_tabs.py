"""
UI tests for the Administration page tabs (admin.html).

The Administration console is a single Alpine root whose left sidebar switches
`activeTab` between panels. Each panel is a `<div x-show="activeTab === '...'">`
whose first child is a `<div class="data-card">` with an `<h2
class="data-card-title">` heading — that heading is the stable "this panel is
live" hook (the panel body is data-driven and varies run to run).

Eight of these tabs previously had no coverage at all (the coverage-gap audit):
Create Sangha Sevi, Create Organization, Person Directory, Organization
Hierarchy, Assign Sakhas, Reference Data, Geography, System Settings. These
tests assert each tab is reachable from the sidebar and renders its panel — the
first line of defence against a nav rename or an `activeTab` string drifting
away from its panel guard.

Selectors are the real ones in admin.html (verified against source): nav items
are `.nav-item` (clicked via the shared `click_nav_item` helper), panel
headings are `h2.data-card-title`. `data-card-title` text is reused across
panels (e.g. "User Accounts", "Role Assignments"), so every assertion is
scoped to the exact heading string.

Two tabs are permission-gated in the sidebar (Create Organization →
`isNssAdmin`, Create Sangha Sevi → `canManageUsers`); the `admin_page` fixture
logs in as SS1 (NSS_ERP_ADMIN / super-admin), so both are present.

Requires a live server + Postgres (BASE_URL http://127.0.0.1:8001). Run with:
    python3 -m pytest tests/ui/test_ui_admin_tabs.py
"""

import pytest
from playwright.sync_api import expect

from tests.ui.conftest import wait_for_alpine, click_nav_item

pytestmark = pytest.mark.ui


# (sidebar nav text, exact panel heading that appears only when the tab is live)
ADMIN_TABS = [
    ("Create Sangha Sevi", "Create Sangha Sevi"),
    ("Create Organization", "Create New Organization"),
    ("Person Directory", "Person Directory"),
    ("Organization Hierarchy", "Organization Hierarchy"),
    ("Assign Sakhas", "Assign Sakhas to Anchalika/Zilla Sangha"),
    ("Reference Data", "Reference Data"),
    ("Geography", "Geography"),
    ("System Settings", "System Settings"),
]


@pytest.fixture
def admin_console(admin_page, base_url):
    """Admin page (SS1) navigated to /admin with Alpine ready."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    return admin_page


@pytest.mark.parametrize(
    "nav_text,heading",
    ADMIN_TABS,
    ids=[t[0].replace(" ", "-").lower() for t in ADMIN_TABS],
)
def test_admin_tab_renders(admin_console, nav_text, heading):
    """Clicking each sidebar item shows its panel heading."""
    page = admin_console
    click_nav_item(page, nav_text)
    wait_for_alpine(page)
    panel_heading = page.locator("h2.data-card-title", has_text=heading)
    expect(panel_heading.first).to_be_visible(timeout=10_000)


def test_admin_sidebar_lists_all_gap_tabs(admin_console):
    """Every audited tab's nav item is present in the sidebar for a super-admin."""
    page = admin_console
    for nav_text, _ in ADMIN_TABS:
        item = page.locator(".nav-item", has_text=nav_text)
        expect(item.first).to_be_visible()
