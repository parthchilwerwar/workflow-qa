"""Dashboard page object for WorkFlow Pro.

Represents the authenticated landing area. Exposes helpers to read the current
tenant/user context and to navigate onward to the Projects area — used by the
multi-tenant isolation and integration tests.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class DashboardPage(BasePage):
    """Page object for the post-login dashboard."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------
    @property
    def container(self):
        """Root dashboard container — the readiness marker after login."""
        return self.by_test_id("dashboard")

    @property
    def welcome_message(self):
        return self.by_test_id("welcome-message")

    @property
    def tenant_badge(self):
        """Element displaying the active tenant/organisation name."""
        return self.by_test_id("tenant-name")

    @property
    def user_role_badge(self):
        """Element displaying the signed-in user's role."""
        return self.by_test_id("user-role")

    @property
    def projects_nav_link(self):
        return self.page.get_by_role("link", name="Projects")

    # ------------------------------------------------------------------
    # Assertions / queries
    # ------------------------------------------------------------------
    def expect_loaded(self) -> None:
        """Assert the dashboard has finished rendering."""
        self.expect_visible(self.container)

    def expect_tenant(self, tenant_name: str) -> None:
        """Assert the dashboard shows the expected tenant (isolation check)."""
        self.expect_text(self.tenant_badge, tenant_name)

    def expect_role(self, role: str) -> None:
        """Assert the signed-in user has the expected role (RBAC check)."""
        self.expect_text(self.user_role_badge, role)

    def get_tenant_name(self) -> str:
        """Return the currently displayed tenant name."""
        return (self.tenant_badge.inner_text() or "").strip()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def open_projects(self) -> None:
        """Navigate to the Projects area from the dashboard."""
        logger.info("Opening Projects from dashboard")
        self.click(self.projects_nav_link)
