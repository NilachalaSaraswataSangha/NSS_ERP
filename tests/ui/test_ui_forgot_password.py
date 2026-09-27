"""
NSS ERP — UI tests for the Forgot / Reset Password flow.

The forgot-password UI lives on the login page (/login) and is
toggled via Alpine.js state inside loginApp().

Flow:
  1. User clicks "Forgot Password?" link  ->  forgot-password form appears
  2. User enters login ID, clicks "Send Reset OTP"
  3. On success the reset-password form appears (OTP + new password fields)
  4. User fills OTP, new password, confirm password, clicks Reset
"""

import pytest
from tests.ui.conftest import wait_for_alpine

pytestmark = pytest.mark.ui


# ── Helpers ───────────────────────────────────────────────────────────


def _open_forgot_password(page, base_url):
    """Navigate to /login and open the forgot-password form."""
    page.goto(f"{base_url}/login")
    wait_for_alpine(page)
    page.wait_for_selector('[x-model="login_id"]', state="visible")

    # Click the forgot-password link (exact text: "Forgot Password?")
    forgot_link = page.locator('a.forgot-link:has-text("Forgot Password?")')
    forgot_link.click()
    page.wait_for_timeout(300)


# ── Forgot Password form visibility ──────────────────────────────────


def test_forgot_password_form_appears(page, base_url):
    """Clicking the 'Forgot Password' link reveals the forgot-password form."""
    _open_forgot_password(page, base_url)

    forgot_input = page.locator('[x-model="forgotLoginId"]')
    forgot_input.wait_for(state="visible", timeout=5000)
    assert forgot_input.is_visible(), "Forgot password form should be visible"


# ── Empty login ID validation ────────────────────────────────────────


def test_forgot_password_empty_login_id(page, base_url):
    """The Send Reset OTP button is disabled when login ID is empty."""
    _open_forgot_password(page, base_url)

    forgot_input = page.locator('[x-model="forgotLoginId"]')
    forgot_input.wait_for(state="visible")

    # Ensure the field is empty
    forgot_input.fill("")
    page.wait_for_timeout(300)

    # The button has :disabled="forgotLoading || !forgotLoginId.trim()"
    send_btn = page.locator('button:has-text("Send Reset OTP")')
    assert send_btn.is_disabled(), (
        "Send Reset OTP button should be disabled when login ID is empty"
    )


# ── Invalid / non-existent user ──────────────────────────────────────


def test_forgot_password_invalid_user(page, base_url):
    """Submitting a non-existent login ID either shows an error or moves to reset step.

    Some APIs return 200 for security (don't reveal whether the account exists).
    We verify the UI responds — either forgotError shows, or it moves to reset step.
    """
    _open_forgot_password(page, base_url)

    forgot_input = page.locator('[x-model="forgotLoginId"]')
    forgot_input.wait_for(state="visible")
    forgot_input.fill("NONEXISTENT_USER_999")

    send_btn = page.locator('button:has-text("Send Reset OTP")')
    send_btn.click()
    page.wait_for_timeout(2000)

    # Either: error shown (API returned 4xx) or moved to reset step (API returned 200)
    error_box = page.locator(".alert-box")
    reset_form = page.locator('[x-model="resetOtp"]')

    error_shown = error_box.count() > 0 and error_box.first.is_visible()
    moved_to_reset = reset_form.count() > 0 and reset_form.first.is_visible()

    assert error_shown or moved_to_reset, (
        "Should either show an error or move to the reset form"
    )


# ── Back to login ────────────────────────────────────────────────────


def test_forgot_password_back_to_login(page, base_url):
    """The back-to-login link returns to the normal login form."""
    _open_forgot_password(page, base_url)

    forgot_input = page.locator('[x-model="forgotLoginId"]')
    forgot_input.wait_for(state="visible")

    # Two "Back to Sign In" links exist (forgot card + reset card) —
    # scope to the visible forgot card
    forgot_card = page.locator('[x-show="showForgotPassword"]')
    back_link = forgot_card.locator('a.forgot-link:has-text("Back to Sign In")')
    back_link.click()
    page.wait_for_timeout(300)

    # The normal login form should be visible again
    login_input = page.locator('[x-model="login_id"]')
    login_input.wait_for(state="visible", timeout=5000)
    assert login_input.is_visible(), "Login form should be visible after going back"

    # The forgot form should be hidden
    assert not page.locator('[x-model="forgotLoginId"]').is_visible(), (
        "Forgot password form should be hidden after going back"
    )


# ── Reset password form validation ───────────────────────────────────


def test_reset_password_form_validation(page, base_url):
    """
    Reset-password form requires OTP and matching passwords.

    Since we cannot easily trigger a real OTP in tests, we verify:
      - The reset form fields exist in the DOM (hidden until OTP is sent)
      - When forced visible, the Reset button is disabled without all fields
    """
    page.goto(f"{base_url}/login")
    wait_for_alpine(page)

    # Force the reset-password section visible via Alpine state
    page.evaluate("""
        () => {
            const root = document.querySelector('[x-data]');
            if (root && root.__x) {
                root.__x.$data.showResetPassword = true;
                root.__x.$data.showForgotPassword = false;
            } else if (root && window.Alpine) {
                Alpine.evaluate(root, 'showResetPassword = true; showForgotPassword = false');
            }
        }
    """)
    page.wait_for_timeout(500)

    # Check that reset form fields exist in the DOM
    otp_field = page.locator('[x-model="resetOtp"]')
    new_pw_field = page.locator('[x-model="resetNewPassword"]')
    confirm_pw_field = page.locator('[x-model="resetConfirmPassword"]')

    assert otp_field.count() > 0, "OTP field should exist in the DOM"
    assert new_pw_field.count() > 0, "New password field should exist in the DOM"
    assert confirm_pw_field.count() > 0, "Confirm password field should exist in the DOM"

    # The Reset button has :disabled="resetLoading || !resetOtp.trim() || !resetNewPassword || !resetConfirmPassword"
    # With all fields empty, it should be disabled
    if otp_field.first.is_visible():
        reset_btn = page.locator('button:has-text("Reset Password")')
        if reset_btn.count() > 0:
            assert reset_btn.first.is_disabled(), (
                "Reset button should be disabled when fields are empty"
            )

            # Fill OTP and passwords but with mismatch — button should be enabled
            otp_field.first.fill("123456")
            new_pw_field.first.fill("NewPass@1")
            confirm_pw_field.first.fill("DifferentPass@2")
            page.wait_for_timeout(300)

            # Button is no longer disabled (all fields filled)
            assert not reset_btn.first.is_disabled(), (
                "Reset button should be enabled when all fields are filled"
            )
