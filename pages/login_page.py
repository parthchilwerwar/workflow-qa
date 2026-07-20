"""Login page object for WorkFlow Pro.

Encapsulates the authentication flow, including **optional 2FA handling** and
robust post-login synchronisation. This is the corrected, non-flaky version of
the login logic discussed in Part 1 of the assessment:

* waits for the ``/dashboard`` URL with a tolerant regex (trailing slash,
  query params, tenant sub-paths);
* uses a retrying ``expect(...)`` on a stable ``data-testid`` element rather
  than a one-shot ``is_visible()``.
"""

from __future__ import annotations

import logging
import re

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage

logger = logging.getLogger(__name__)

# Tolerant matcher: accepts /dashboard, /dashboard/, /dashboard?next=... etc.
_DASHBOARD_URL = re.compile(r".*/dashboard(?:/|\?.*)?$")


class LoginPage(BasePage):
    """Page object for the ``/login`` screen."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Locators  (resilient: role- and label-based, test-id for the marker)
    # ------------------------------------------------------------------
    @property
    def email_input(self):
        return self.page.get_by_label("Email")

    @property
    def password_input(self):
        return self.page.get_by_label("Password")

    @property
    def submit_button(self):
        return self.page.get_by_role("button", name=re.compile("sign in|login", re.I))

    @property
    def otp_input(self):
        return self.page.get_by_label(re.compile("verification code|otp", re.I))

    @property
    def otp_submit_button(self):
        return self.page.get_by_role("button", name=re.compile("verify|continue", re.I))

    @property
    def error_banner(self):
        return self.page.get_by_test_id("login-error")

    # ------------------------------------------------------------------
    # High-level flows
    # ------------------------------------------------------------------
    def load(self, login_url: str) -> None:
        """Open the login page."""
        self.goto(login_url, wait_until="domcontentloaded")
        self.expect_visible(self.email_input)

    def submit_credentials(self, email: str, password: str) -> None:
        """Fill and submit the credentials form."""
        logger.info("Submitting credentials for %s", email)
        self.fill(self.email_input, email)
        self.fill(self.password_input, password)
        self.click(self.submit_button)

    def handle_optional_2fa(self, otp: str | None) -> None:
        """Complete the 2FA challenge **only if** the app presents one.

        Probes briefly for the OTP field. If no challenge appears the method
        returns quietly (accounts without 2FA are not penalised). If a challenge
        *is* presented but no test OTP is configured, a clear error is raised so
        the failure is actionable rather than a mysterious timeout later.
        """
        try:
            self.otp_input.wait_for(state="visible", timeout=3_000)
        except PlaywrightTimeoutError:
            logger.debug("No 2FA challenge presented; continuing")
            return

        # A 2FA challenge is on screen — it must be satisfied to proceed.
        if not otp:
            raise RuntimeError("2FA challenge presented but no test OTP configured (set TEST_OTP).")
        logger.info("2FA challenge detected — submitting test OTP")
        self.fill(self.otp_input, otp)
        self.click(self.otp_submit_button)

    def wait_for_authenticated(self, *, nav_timeout: int, dashboard_timeout: int) -> None:
        """Synchronise on a meaningful post-login application state.

        This is the key fix for the flaky test: we wait for the dashboard URL
        AND for the dashboard container to render, instead of asserting the URL
        immediately after clicking.
        """
        self.page.wait_for_url(_DASHBOARD_URL, timeout=nav_timeout)
        expect(self.by_test_id("dashboard")).to_be_visible(timeout=dashboard_timeout)

    def login(
        self,
        login_url: str,
        email: str,
        password: str,
        *,
        otp: str | None = None,
        nav_timeout: int = 30_000,
        dashboard_timeout: int = 20_000,
    ) -> None:
        """End-to-end reliable login: load → submit → 2FA → wait for dashboard."""
        self.load(login_url)
        self.submit_credentials(email, password)
        self.handle_optional_2fa(otp)
        self.wait_for_authenticated(nav_timeout=nav_timeout, dashboard_timeout=dashboard_timeout)

    def expect_login_error(self, message: str | None = None) -> None:
        """Assert an authentication error is shown (negative-path helper)."""
        self.expect_visible(self.error_banner)
        if message:
            self.expect_text(self.error_banner, message)
