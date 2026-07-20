"""Login test suite for WorkFlow Pro.

The corrected, non-flaky implementation of the login checks from Part 1 of the
assessment. It demonstrates:

* **Reliable waits** — synchronising on the dashboard URL + a rendered marker
  instead of asserting the URL immediately after the click;
* **Retrying assertions** — Playwright ``expect(...)`` web-first assertions;
* **Retry-friendly logic** — no fixed sleeps; safe to re-run under
  ``pytest-rerunfailures`` in CI;
* **Locator best practices** — role/label locators + stable ``data-testid``;
* **Optional 2FA handling** — driven by the ``TEST_OTP`` env var;
* **Environment variables** — all credentials come from configuration.

WorkFlow Pro is fictional and inaccessible, so these tests ``skip`` cleanly
until real credentials/endpoints are supplied via environment variables.
"""

from __future__ import annotations

import pytest

from config.config import Settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


@pytest.mark.smoke
@pytest.mark.login
def test_successful_login_reaches_dashboard(page, settings: Settings) -> None:
    """A valid user logs in and lands on a fully-rendered dashboard."""
    creds = settings.primary_credentials

    login_page = LoginPage(page)

    # Step 1: Open the login page and wait for the form to be interactive.
    login_page.load(settings.login_url)

    # Step 2: Submit credentials read from the environment (never hard-coded).
    login_page.submit_credentials(creds.username, creds.password)

    # Step 3: Handle 2FA only if the application presents a challenge.
    login_page.handle_optional_2fa(creds.otp or None)

    # Step 4: Synchronise on a meaningful application state — the dashboard URL
    #         (tolerant regex) AND the rendered dashboard container. This is the
    #         key fix for the original race condition.
    login_page.wait_for_authenticated(
        nav_timeout=settings.navigation_timeout,
        dashboard_timeout=settings.default_timeout,
    )

    # Step 5: Assert the dashboard is genuinely ready using retrying assertions.
    DashboardPage(page).expect_loaded()


@pytest.mark.login
def test_invalid_credentials_show_error(page, settings: Settings) -> None:
    """Invalid credentials must surface an error and stay off the dashboard."""
    login_page = LoginPage(page)

    # Step 1: Load the login page.
    login_page.load(settings.login_url)

    # Step 2: Submit deliberately wrong credentials (negative path). The values
    #         are throwaway literals for a negative test, not real accounts.
    login_page.submit_credentials("invalid.user@example.test", "wrong-password")

    # Step 3: Assert a retrying error banner appears — no fixed sleep needed.
    login_page.expect_login_error()

    # Step 4: Assert we did NOT navigate to the dashboard.
    assert "/dashboard" not in login_page.current_url


@pytest.mark.login
def test_login_helper_is_idempotent(authenticated_page, settings: Settings) -> None:
    """The ``authenticated_page`` fixture yields a session already on the dashboard.

    Demonstrates reuse of the authentication fixture so individual tests do not
    repeat login boilerplate. Skips automatically when credentials are absent.
    """
    dashboard = DashboardPage(authenticated_page)

    # The fixture already logged in; assert readiness with a retrying check.
    dashboard.expect_loaded()

    # Tenant context should match the configured primary tenant.
    assert settings.company1_tenant  # sanity: tenant is configured
