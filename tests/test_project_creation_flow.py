"""End-to-end API + UI integration flow for WorkFlow Pro.

Implements the integration test from Part 3 of the assessment:

    generate unique data -> API creates project -> verify schema ->
    UI (desktop) validates -> mobile viewport validates ->
    Company 2 cannot access (API) -> cleanup.

Strategy (per the assessment): set data up through the API because it is faster
and more reliable, then validate through the UI. Verification uses stable
project IDs, not visible-text matching. WorkFlow Pro is fictional, so the test
skips cleanly until real credentials/endpoints are supplied.
"""

from __future__ import annotations

from types import ModuleType

import pytest

from api.project_api import ProjectAPI
from config.config import Settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.projects_page import ProjectsPage


def _login(page, settings: Settings, creds) -> None:
    """Reliable login helper reused for each tenant/context."""
    LoginPage(page).login(
        settings.login_url,
        creds.username,
        creds.password,
        otp=creds.otp or None,
        nav_timeout=settings.navigation_timeout,
        dashboard_timeout=settings.default_timeout,
    )


@pytest.mark.integration
@pytest.mark.mobile
def test_project_creation_flow(
    context,
    mobile_context,
    company1_api: ProjectAPI,
    company2_api: ProjectAPI,
    project_factory: ModuleType,
    project_cleanup,
    settings: Settings,
) -> None:
    """Create via API, validate on desktop + mobile, deny Company 2, clean up."""
    creds1 = settings.primary_credentials
    creds2 = settings.secondary_credentials

    # Guard: skip cleanly if the environment is not fully configured.
    if not (creds1.api_token and creds1.has_login and creds2.has_login):
        pytest.skip(
            "Integration flow requires COMPANY1_API_TOKEN + login credentials for both tenants."
        )

    # ------------------------------------------------------------------
    # Step 1: Generate UNIQUE data and create the project via Company 1 API.
    # ------------------------------------------------------------------
    payload = project_factory.new_project_payload()
    project = company1_api.create_project(payload)

    # Step 2: Verify the returned project schema (contract sanity check).
    for required_key in ("id", "name", "status"):
        assert required_key in project, f"API response missing '{required_key}'"
    assert project["name"] == payload["name"]

    project_id = project["id"]
    project_cleanup(project_id)  # ensure teardown even if later steps fail

    # ------------------------------------------------------------------
    # Step 3: Validate the project in a DESKTOP browser as Company 1.
    # ------------------------------------------------------------------
    desktop_page = context.new_page()
    _login(desktop_page, settings, creds1)
    DashboardPage(desktop_page).expect_loaded()

    projects_page = ProjectsPage(desktop_page)
    projects_page.load(settings.base_url)
    # Assert by stable project ID (retrying) — not by fragile visible text.
    projects_page.expect_project_visible(project_id, payload["name"])

    # ------------------------------------------------------------------
    # Step 4: Responsive validation on a MOBILE viewport (same login flow).
    # ------------------------------------------------------------------
    mobile_page = mobile_context.new_page()
    _login(mobile_page, settings, creds1)
    mobile_projects = ProjectsPage(mobile_page)
    mobile_projects.load(settings.base_url)
    mobile_projects.expect_project_visible(project_id, payload["name"])

    # ------------------------------------------------------------------
    # Step 5: Tenant isolation — Company 2 must NOT access the project.
    #         Verified at the API layer (authoritative) via a 403/404.
    # ------------------------------------------------------------------
    assert company2_api.can_access_project(project_id) is False

    # ------------------------------------------------------------------
    # Step 6: Cleanup — handled by the project_cleanup fixture in teardown,
    #         which deletes the project through the Company 1 API.
    # ------------------------------------------------------------------
