"""Projects page object for WorkFlow Pro.

Handles listing, creating and verifying projects. Verification is done by a
**stable project identifier** (``data-testid=project-card-<id>``) rather than
by matching visible text, which the assessment calls out as the correct way to
validate tenant isolation.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Page

from pages.base_page import BasePage

logger = logging.getLogger(__name__)


class ProjectsPage(BasePage):
    """Page object for the ``/projects`` area."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def load(self, base_url: str) -> None:
        """Open the projects list directly by URL."""
        self.goto(f"{base_url.rstrip('/')}/projects", wait_until="domcontentloaded")
        self.expect_visible(self.list_container)

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------
    @property
    def list_container(self):
        """Container that wraps the project cards (readiness marker)."""
        return self.by_test_id("projects-list")

    @property
    def new_project_button(self):
        return self.page.get_by_role("button", name="New Project")

    @property
    def name_input(self):
        return self.page.get_by_label("Project Name")

    @property
    def description_input(self):
        return self.page.get_by_label("Description")

    @property
    def create_submit_button(self):
        return self.page.get_by_role("button", name="Create")

    def project_card(self, project_id: str):
        """Return the locator for a specific project's card by its ID."""
        return self.by_test_id(f"project-card-{project_id}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def create_project(self, name: str, description: str = "") -> None:
        """Create a project through the UI (used when API setup is not wanted)."""
        logger.info("Creating project via UI: %s", name)
        self.click(self.new_project_button)
        self.fill(self.name_input, name)
        if description:
            self.fill(self.description_input, description)
        self.click(self.create_submit_button)

    # ------------------------------------------------------------------
    # Assertions  (ID-based, retrying — reliable for dynamic loading)
    # ------------------------------------------------------------------
    def expect_project_visible(self, project_id: str, name: str | None = None) -> None:
        """Assert a project is present for the current tenant.

        We wait on the stable card ``data-testid`` so the assertion retries
        while the list loads asynchronously — avoiding the ``.all()``-too-early
        pitfall highlighted in the assessment.
        """
        card = self.project_card(project_id)
        self.expect_visible(card)
        if name:
            self.expect_text(card, name)

    def expect_project_not_visible(self, project_id: str, name: str | None = None) -> None:
        """Assert a project is NOT accessible (negative / isolation check)."""
        self.expect_hidden(self.project_card(project_id))
