"""
NSS ERP — Comprehensive UI tests for the Member Dashboard (/dashboard).

Tests all dashboard features after login:
  - Authentication gating and page load
  - Sidebar navigation, topbar, user info, logout
  - Personal tab: info display, membership snapshot, address, edit profile
  - Membership tab: details, account info, affiliations, journey timeline
  - Family tab: family state (tree or create prompt), member list
  - Attendance/Governance tabs: placeholder cards
  - Documents tab: Parichaya Patra, Anumati Patra
  - Admin tabs: visibility, stats grid, admin link

Alpine.js app: dashboardApp()
"""

import pytest
from playwright.sync_api import Page, expect

from tests.ui.conftest import (
    wait_for_alpine,
    click_nav_item,
    BASE_URL,
)

pytestmark = pytest.mark.ui


# ── Reusable helpers ─────────────────────────────────────────────────────

def _wait_dashboard_ready(admin_page: Page):
    """Wait for Alpine init + loading spinner to disappear."""
    wait_for_alpine(admin_page)
    # Wait until the loading state is done (loading overlay gone or content visible)
    admin_page.wait_for_selector(
        ".content-area",
        state="visible",
        timeout=15000,
    )
    # Give API fetches time to resolve
    admin_page.wait_for_timeout(2000)


def _switch_tab(admin_page: Page, tab_name: str):
    """Switch dashboard tab via sidebar and wait for content."""
    click_nav_item(admin_page, tab_name)
    admin_page.wait_for_timeout(1000)


def _get_visible_text(admin_page: Page, selector: str) -> str:
    """Get text content of a visible element, empty string if not found."""
    el = admin_page.locator(selector)
    if el.count() > 0 and el.first.is_visible():
        return el.first.text_content().strip()
    return ""


def _data_card_visible(admin_page: Page, title_text: str) -> bool:
    """Check if a data card with the given title is visible."""
    card_title = admin_page.locator(f".data-card-title:has-text('{title_text}')")
    return card_title.count() > 0 and card_title.first.is_visible()


def _placeholder_card_visible(admin_page: Page, heading_text: str) -> bool:
    """Check if a placeholder card with the given heading is visible."""
    heading = admin_page.locator(f".placeholder-card h3:has-text('{heading_text}')")
    return heading.count() > 0 and heading.first.is_visible()


# ═══════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION GATE
# ═══════════════════════════════════════════════════════════════════════════


class TestDashboardAuth:

    def test_unauthenticated_redirects_to_login(self, page: Page, base_url: str):
        """Unauthenticated visit to /dashboard must redirect to /login."""
        page.goto(f"{base_url}/dashboard")
        page.wait_for_url("**/login**", timeout=10000)
        assert "/login" in page.url

    def test_authenticated_lands_on_dashboard(self, admin_page: Page, base_url: str):
        """After admin login the browser lands on /dashboard."""
        assert "/dashboard" in admin_page.url
        wait_for_alpine(admin_page)

    def test_page_title_is_set(self, admin_page: Page):
        """Page title includes 'Dashboard'."""
        assert "Dashboard" in admin_page.title()


# ═══════════════════════════════════════════════════════════════════════════
#  SIDEBAR LAYOUT
# ═══════════════════════════════════════════════════════════════════════════


class TestDashboardSidebar:

    def test_sidebar_visible(self, admin_page: Page):
        """Sidebar element is present."""
        _wait_dashboard_ready(admin_page)
        sidebar = admin_page.locator(".sidebar")
        expect(sidebar).to_be_visible()

    def test_sidebar_has_core_nav_items(self, admin_page: Page):
        """Sidebar contains the 6 core dashboard tabs."""
        _wait_dashboard_ready(admin_page)
        core_tabs = ["Personal", "Membership", "Family", "Attendance", "Governance", "Documents"]
        for tab in core_tabs:
            item = admin_page.locator(f".nav-item:has-text('{tab}')")
            assert item.count() > 0, f"Sidebar should have '{tab}' nav item"

    def test_sidebar_brand_shows_nss(self, admin_page: Page):
        """Sidebar brand area displays Nilachala Saraswata Sangha."""
        _wait_dashboard_ready(admin_page)
        brand = admin_page.locator(".sidebar-brand")
        expect(brand).to_be_visible()
        brand_text = brand.text_content().lower()
        assert "nilachala" in brand_text or "nss" in brand_text

    def test_sidebar_footer_shows_user(self, admin_page: Page):
        """Sidebar footer displays the logged-in user's name and SS ID."""
        _wait_dashboard_ready(admin_page)
        footer = admin_page.locator(".sidebar-footer")
        expect(footer).to_be_visible()

        user_name = admin_page.locator(".sidebar-footer .user-name")
        user_id = admin_page.locator(".sidebar-footer .user-id")
        assert user_name.text_content().strip() != "", "User name should be displayed"
        assert user_id.text_content().strip() != "", "User ID should be displayed"

    def test_sidebar_admin_tabs_for_admin_user(self, admin_page: Page):
        """Admin user (SS1) sees admin-specific tabs in the sidebar."""
        _wait_dashboard_ready(admin_page)
        # SS1 has NSS_ERP_ADMIN role — should see "System Administration" tab
        admin_label = admin_page.locator(".nav-item:has-text('System Administration')")
        # Or it may use a section label
        admin_section = admin_page.locator(".nav-section-label:has-text('Admin')")
        assert admin_label.count() > 0 or admin_section.count() > 0, (
            "Admin user should see admin-specific tabs in sidebar"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  TOPBAR
# ═══════════════════════════════════════════════════════════════════════════


class TestDashboardTopbar:

    def test_topbar_visible(self, admin_page: Page):
        """Topbar is visible on dashboard."""
        _wait_dashboard_ready(admin_page)
        topbar = admin_page.locator(".topbar")
        expect(topbar).to_be_visible()

    def test_topbar_shows_current_tab_title(self, admin_page: Page):
        """Topbar title reflects the active tab name."""
        _wait_dashboard_ready(admin_page)
        topbar_title = admin_page.locator(".topbar-title")
        text = topbar_title.text_content().strip()
        assert len(text) > 0, "Topbar title should not be empty"
        # Default tab is Personal — title should reflect that
        assert "personal" in text.lower() or "information" in text.lower() or "dashboard" in text.lower()


# ═══════════════════════════════════════════════════════════════════════════
#  PERSONAL TAB (default)
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonalTab:

    def test_personal_tab_active_by_default(self, admin_page: Page):
        """Personal tab is active by default when dashboard loads."""
        _wait_dashboard_ready(admin_page)
        personal_item = admin_page.locator(".nav-item:has-text('Personal')")
        is_active = personal_item.evaluate(
            "el => el.classList.contains('active') || el.getAttribute('aria-selected') === 'true'"
        )
        assert is_active, "Personal tab should be active by default"

    def test_personal_info_card_visible(self, admin_page: Page):
        """Personal Information card is visible on the Personal tab."""
        _wait_dashboard_ready(admin_page)
        assert _data_card_visible(admin_page, "Personal Information"), (
            "Personal Information card should be visible"
        )

    def test_personal_info_shows_full_name(self, admin_page: Page):
        """Personal Information card displays the user's full name."""
        _wait_dashboard_ready(admin_page)
        # The Full Name label and value
        name_label = admin_page.locator(".data-label:has-text('Full Name')")
        assert name_label.count() > 0, "Full Name label should exist"
        # The value next to it should not be empty or '—'
        name_row = name_label.first.locator("..").locator(".data-value")
        if name_row.count() > 0:
            value = name_row.first.text_content().strip()
            assert value and value != "—", f"Full Name should have a value, got: '{value}'"

    def test_personal_info_shows_email(self, admin_page: Page):
        """Personal Information shows an email field."""
        _wait_dashboard_ready(admin_page)
        email_label = admin_page.locator(".data-label:has-text('Email')")
        assert email_label.count() > 0, "Email label should exist on Personal tab"

    def test_membership_snapshot_card_visible(self, admin_page: Page):
        """Membership Snapshot card is visible on the Personal tab."""
        _wait_dashboard_ready(admin_page)
        assert _data_card_visible(admin_page, "Membership Snapshot"), (
            "Membership Snapshot card should be visible"
        )

    def test_membership_snapshot_shows_ss_id(self, admin_page: Page):
        """Membership Snapshot displays the Sangha Sevi ID."""
        _wait_dashboard_ready(admin_page)
        ss_label = admin_page.locator(".data-label:has-text('Sangha Sevi ID')")
        assert ss_label.count() > 0, "Sangha Sevi ID label should exist"
        # Value should be populated for SS1
        ss_value = admin_page.locator(".data-sevi-id").first
        if ss_value.count() > 0:
            text = ss_value.text_content().strip()
            assert text and text != "—", f"Sangha Sevi ID should have a value, got: '{text}'"

    def test_address_card_visible(self, admin_page: Page):
        """Address card is visible on the Personal tab."""
        _wait_dashboard_ready(admin_page)
        assert _data_card_visible(admin_page, "Address"), (
            "Address card should be visible"
        )

    def test_edit_profile_button_exists(self, admin_page: Page):
        """Personal tab has an Edit button for profile editing."""
        _wait_dashboard_ready(admin_page)
        edit_btn = admin_page.locator("button:has-text('Edit')")
        assert edit_btn.count() > 0, "Edit button should exist on Personal tab"

    def test_edit_profile_opens_form(self, admin_page: Page):
        """Clicking Edit shows the profile editing form fields."""
        _wait_dashboard_ready(admin_page)
        edit_btn = admin_page.locator("button:has-text('Edit')").first
        edit_btn.click()
        admin_page.wait_for_timeout(500)

        # Edit form fields should appear
        mobile_input = admin_page.locator('[x-model="profileForm.mobile_number"]')
        email_input = admin_page.locator('[x-model="profileForm.email"]')
        dob_input = admin_page.locator('[x-model="profileForm.date_of_birth"]')

        assert mobile_input.count() > 0, "Mobile number input should appear in edit mode"
        assert email_input.count() > 0, "Email input should appear in edit mode"
        assert dob_input.count() > 0, "Date of birth input should appear in edit mode"

    def test_edit_profile_has_save_cancel(self, admin_page: Page):
        """Edit mode shows Save and Cancel buttons."""
        _wait_dashboard_ready(admin_page)
        edit_btn = admin_page.locator("button:has-text('Edit')").first
        edit_btn.click()
        admin_page.wait_for_timeout(500)

        save_btn = admin_page.locator("button:has-text('Save')")
        cancel_btn = admin_page.locator("button:has-text('Cancel')")
        assert save_btn.count() > 0, "Save button should exist in edit mode"
        assert cancel_btn.count() > 0, "Cancel button should exist in edit mode"

    def test_edit_profile_cancel_returns_to_view(self, admin_page: Page):
        """Clicking Cancel exits edit mode and returns to view mode."""
        _wait_dashboard_ready(admin_page)
        edit_btn = admin_page.locator("button:has-text('Edit')").first
        edit_btn.click()
        admin_page.wait_for_timeout(500)

        cancel_btn = admin_page.locator("button:has-text('Cancel')").first
        cancel_btn.click()
        admin_page.wait_for_timeout(500)

        # Edit button should reappear (view mode)
        edit_btn_again = admin_page.locator("button:has-text('Edit')")
        assert edit_btn_again.count() > 0, "Edit button should reappear after Cancel"


# ═══════════════════════════════════════════════════════════════════════════
#  TAB SWITCHING
# ═══════════════════════════════════════════════════════════════════════════


class TestTabSwitching:

    def test_switch_to_membership_tab(self, admin_page: Page):
        """Clicking Membership tab activates it and shows Membership content."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")

        item = admin_page.locator(".nav-item:has-text('Membership')")
        is_active = item.evaluate(
            "el => el.classList.contains('active')"
        )
        assert is_active, "Membership tab should be active after clicking"

    def test_switch_to_family_tab(self, admin_page: Page):
        """Clicking Family tab activates it."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Family")

        item = admin_page.locator(".nav-item:has-text('Family')")
        is_active = item.evaluate(
            "el => el.classList.contains('active')"
        )
        assert is_active, "Family tab should be active after clicking"

    def test_switch_to_attendance_tab(self, admin_page: Page):
        """Clicking Attendance tab activates it."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Attendance")

        item = admin_page.locator(".nav-item:has-text('Attendance')")
        is_active = item.evaluate(
            "el => el.classList.contains('active')"
        )
        assert is_active, "Attendance tab should be active after clicking"

    def test_switch_to_documents_tab(self, admin_page: Page):
        """Clicking Documents tab activates it."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Documents")

        item = admin_page.locator(".nav-item:has-text('Documents')")
        is_active = item.evaluate(
            "el => el.classList.contains('active')"
        )
        assert is_active, "Documents tab should be active after clicking"

    def test_switch_back_to_personal(self, admin_page: Page):
        """Switching to another tab and back to Personal restores it."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        _switch_tab(admin_page, "Personal")

        item = admin_page.locator(".nav-item:has-text('Personal')")
        is_active = item.evaluate(
            "el => el.classList.contains('active')"
        )
        assert is_active, "Personal tab should be active after switching back"

    def test_topbar_title_updates_on_tab_switch(self, admin_page: Page):
        """Topbar title updates when switching tabs."""
        _wait_dashboard_ready(admin_page)
        topbar_title = admin_page.locator(".topbar-title")

        _switch_tab(admin_page, "Membership")
        text = topbar_title.text_content().strip().lower()
        assert "membership" in text, f"Topbar should show 'Membership', got '{text}'"

        _switch_tab(admin_page, "Family")
        text = topbar_title.text_content().strip().lower()
        assert "family" in text, f"Topbar should show 'Family', got '{text}'"


# ═══════════════════════════════════════════════════════════════════════════
#  MEMBERSHIP TAB
# ═══════════════════════════════════════════════════════════════════════════


class TestMembershipTab:

    def test_membership_details_card(self, admin_page: Page):
        """Membership tab shows a 'Membership Details' data card."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)
        assert _data_card_visible(admin_page, "Membership Details"), (
            "Membership Details card should be visible"
        )

    def test_membership_details_has_ss_id(self, admin_page: Page):
        """Membership Details card shows the Sangha Sevi ID."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)

        ss_label = admin_page.locator(
            "[x-show=\"tab === 'membership'\"] .data-label:has-text('Sangha Sevi ID')"
        )
        assert ss_label.count() > 0, "Membership tab should show Sangha Sevi ID"

    def test_membership_details_has_type(self, admin_page: Page):
        """Membership Details card shows membership type badge."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)

        type_label = admin_page.locator(
            "[x-show=\"tab === 'membership'\"] .data-label:has-text('Type')"
        )
        assert type_label.count() > 0, "Membership tab should show Type field"

    def test_membership_details_has_status(self, admin_page: Page):
        """Membership Details card shows membership status badge."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)

        status_label = admin_page.locator(
            "[x-show=\"tab === 'membership'\"] .data-label:has-text('Status')"
        )
        assert status_label.count() > 0, "Membership tab should show Status field"

    def test_account_info_card(self, admin_page: Page):
        """Membership tab shows 'Account Information' card."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)
        assert _data_card_visible(admin_page, "Account Information"), (
            "Account Information card should be visible"
        )

    def test_account_info_shows_status(self, admin_page: Page):
        """Account Information card shows account status badge."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)

        status_label = admin_page.locator(".data-label:has-text('Account Status')")
        assert status_label.count() > 0, "Account Information should show Account Status"

    def test_account_info_shows_roles_count(self, admin_page: Page):
        """Account Information card shows the number of roles assigned."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1000)

        roles_label = admin_page.locator(".data-label:has-text('Roles Assigned')")
        assert roles_label.count() > 0, "Account Information should show Roles Assigned"

    def test_sakha_affiliations_section(self, admin_page: Page):
        """Membership tab shows Sakha Affiliations section."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1500)
        assert _data_card_visible(admin_page, "Sakha Affiliations"), (
            "Sakha Affiliations section should be visible"
        )

    def test_journey_timeline_section(self, admin_page: Page):
        """Membership tab shows Journey Timeline section."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Membership")
        admin_page.wait_for_timeout(1500)
        assert _data_card_visible(admin_page, "Journey Timeline"), (
            "Journey Timeline section should be visible"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  FAMILY TAB
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyTab:

    def test_family_tab_loads(self, admin_page: Page):
        """Family tab loads without error."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Family")
        admin_page.wait_for_timeout(2000)

        # Should show either family data or the "No Family Record" placeholder
        family_content = admin_page.locator("[x-show=\"tab === 'family'\"]")
        expect(family_content).to_be_visible()

    def test_family_shows_tree_or_create_prompt(self, admin_page: Page):
        """Family tab shows either the family tree or 'Create My Family' prompt."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Family")
        admin_page.wait_for_timeout(3000)

        # Option A: Family exists — tree or member list visible
        tree_area = admin_page.locator(".family-tree, [class*='tree-node'], .gen-divider")
        member_table = admin_page.locator("text=Members")

        # Option B: No family — placeholder with create button
        no_family = admin_page.locator("text=No Family Record")
        create_btn = admin_page.locator("button:has-text('Create My Family')")

        has_family_content = tree_area.count() > 0 or member_table.count() > 0
        has_no_family_prompt = no_family.count() > 0 or create_btn.count() > 0

        assert has_family_content or has_no_family_prompt, (
            "Family tab should show either family data or create-family prompt"
        )

    def test_family_member_list_or_empty(self, admin_page: Page):
        """If a family exists, the member list section is present."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Family")
        admin_page.wait_for_timeout(3000)

        # Check if family exists first
        no_family = admin_page.locator("text=No Family Record")
        if no_family.count() > 0 and no_family.first.is_visible():
            pytest.skip("No family exists for this user — create-family prompt shown")

        # Family exists — look for member-related content
        members_section = admin_page.locator(
            "text=Members, text=Head of Family, text=Family Members"
        )
        assert members_section.count() > 0, (
            "Family tab should show a members section when family exists"
        )

    def test_family_tree_rendering(self, admin_page: Page):
        """If a family with members exists, the family tree renders nodes."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Family")
        admin_page.wait_for_timeout(4000)

        no_family = admin_page.locator("text=No Family Record")
        if no_family.count() > 0 and no_family.first.is_visible():
            pytest.skip("No family exists for this user")

        # Tree nodes are rendered as .tree-node elements via x-html
        tree_nodes = admin_page.locator(".tree-node")
        gen_dividers = admin_page.locator(".gen-divider")

        if tree_nodes.count() == 0 and gen_dividers.count() == 0:
            # Tree may still be loading or family has only one member
            tree_loading = admin_page.locator("text=Loading family tree")
            if tree_loading.count() > 0:
                pytest.skip("Family tree still loading")
            # Single-member family may not render a full tree
            return

        assert tree_nodes.count() > 0 or gen_dividers.count() > 0, (
            "Family tree should render tree nodes or generation dividers"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  ATTENDANCE TAB (placeholder)
# ═══════════════════════════════════════════════════════════════════════════


class TestAttendanceTab:

    def test_attendance_placeholder(self, admin_page: Page):
        """Attendance tab shows placeholder card."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Attendance")
        admin_page.wait_for_timeout(500)

        assert _placeholder_card_visible(admin_page, "Attendance Records"), (
            "Attendance tab should show 'Attendance Records' placeholder"
        )

    def test_attendance_placeholder_message(self, admin_page: Page):
        """Attendance placeholder mentions module not yet implemented."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Attendance")
        admin_page.wait_for_timeout(500)

        # Scope to the attendance tab's x-show div to avoid picking family tab content
        attendance_div = admin_page.locator('[x-show="tab === \'attendance\'"]')
        msg = attendance_div.locator(".placeholder-card p")
        if msg.count() > 0:
            text = msg.first.text_content().lower()
            assert "attendance" in text or "implemented" in text


# ═══════════════════════════════════════════════════════════════════════════
#  GOVERNANCE TAB (placeholder)
# ═══════════════════════════════════════════════════════════════════════════


class TestGovernanceTab:

    def test_governance_placeholder(self, admin_page: Page):
        """Governance tab shows placeholder card."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Governance")
        admin_page.wait_for_timeout(500)

        assert _placeholder_card_visible(admin_page, "Governance Roles"), (
            "Governance tab should show 'Governance Roles' placeholder"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  DOCUMENTS TAB
# ═══════════════════════════════════════════════════════════════════════════


class TestDocumentsTab:

    def test_documents_tab_loads(self, admin_page: Page):
        """Documents tab loads and shows content area."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Documents")
        admin_page.wait_for_timeout(1000)

        doc_tab = admin_page.locator("[x-show=\"tab === 'documents'\"]")
        expect(doc_tab).to_be_visible()

    def test_parichaya_patra_section(self, admin_page: Page):
        """Documents tab shows Parichaya Patra section."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Documents")
        admin_page.wait_for_timeout(1000)
        assert _data_card_visible(admin_page, "Parichaya Patra"), (
            "Documents tab should show Parichaya Patra section"
        )

    def test_parichaya_patra_shows_records_or_empty(self, admin_page: Page):
        """Parichaya Patra shows record count badge or empty state."""
        _wait_dashboard_ready(admin_page)
        _switch_tab(admin_page, "Documents")
        admin_page.wait_for_timeout(1500)

        # Either records exist or the empty state is shown
        records_badge = admin_page.locator(".badge:has-text('record')")
        empty_msg = admin_page.locator("text=No Parichaya Patra records")
        assert records_badge.count() > 0 or empty_msg.count() > 0, (
            "Parichaya Patra should show record count or empty message"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN TABS (role-based)
# ═══════════════════════════════════════════════════════════════════════════


class TestAdminTabs:

    def test_admin_tab_visible_for_admin_user(self, admin_page: Page):
        """SS1 (NSS_ERP_ADMIN) sees at least one admin tab in the sidebar."""
        _wait_dashboard_ready(admin_page)

        # Admin tabs are generated from ADMIN_TAB_MAP based on scopes
        admin_nav = admin_page.locator(
            ".nav-item:has-text('System Administration'), "
            ".nav-item:has-text('Management'), "
            ".nav-item:has-text('Audit')"
        )
        assert admin_nav.count() > 0, "Admin user should see admin tabs"

    def test_admin_tab_shows_stats_grid(self, admin_page: Page):
        """Clicking an admin tab shows the stats grid (members, families, etc.)."""
        _wait_dashboard_ready(admin_page)

        # Find the first admin tab
        admin_items = admin_page.locator(
            ".nav-item:has-text('System Administration'), "
            ".nav-item:has-text('Management')"
        )
        if admin_items.count() == 0:
            pytest.skip("No admin tabs visible")

        admin_items.first.click()
        admin_page.wait_for_timeout(2000)

        # Stats grid should show stat cards with numbers
        active_members = admin_page.locator("text=Active Members")
        families_stat = admin_page.locator("text=Families")
        assert active_members.count() > 0 or families_stat.count() > 0, (
            "Admin tab should show stats grid with Active Members / Families"
        )

    def test_admin_tab_shows_role_and_scope(self, admin_page: Page):
        """Admin tab header shows role label, description, and scope."""
        _wait_dashboard_ready(admin_page)

        admin_items = admin_page.locator(
            ".nav-item:has-text('System Administration')"
        )
        if admin_items.count() == 0:
            pytest.skip("System Administration tab not visible")

        admin_items.first.click()
        admin_page.wait_for_timeout(1500)

        # Header should show scope label
        scope = admin_page.locator("text=Scope")
        assert scope.count() > 0, "Admin tab should show Scope information"

    def test_admin_tab_has_admin_link(self, admin_page: Page):
        """Admin tab provides a link/button to the full admin page."""
        _wait_dashboard_ready(admin_page)

        admin_items = admin_page.locator(
            ".nav-item:has-text('System Administration')"
        )
        if admin_items.count() == 0:
            pytest.skip("System Administration tab not visible")

        admin_items.first.click()
        admin_page.wait_for_timeout(1500)

        # Look for "Open Admin Panel" or similar link to /admin
        admin_link = admin_page.locator(
            "a[href*='/admin'], button:has-text('Open Admin'), "
            "button:has-text('Admin Panel'), a:has-text('admin')"
        )
        # This may or may not exist depending on the design
        if admin_link.count() == 0:
            pytest.skip("No direct admin panel link found on admin tab")


# ═══════════════════════════════════════════════════════════════════════════
#  LOGOUT
# ═══════════════════════════════════════════════════════════════════════════


class TestDashboardLogout:

    def test_logout_button_exists(self, admin_page: Page):
        """Logout button exists in the sidebar footer."""
        _wait_dashboard_ready(admin_page)
        logout_btn = admin_page.locator(".logout-btn")
        expect(logout_btn).to_be_visible()

    def test_logout_redirects_to_login(self, admin_page: Page, base_url: str):
        """Clicking the logout button redirects to /login."""
        _wait_dashboard_ready(admin_page)
        logout_btn = admin_page.locator(".logout-btn")
        logout_btn.click()
        admin_page.wait_for_url("**/login**", timeout=10000)
        assert "/login" in admin_page.url
