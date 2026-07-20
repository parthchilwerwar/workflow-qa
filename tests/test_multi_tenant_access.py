"""Multi-tenant access & RBAC test suite for WorkFlow Pro.

Demonstrates the tenant-isolation strategy from Part 2 of the assessment:

* **Tenant isolation** — Company 2 cannot read Company 1's project (403/404);
* **Role validation** — the signed-in user's role is asserted in the UI;
* **Unique test data** — payloads come from the shared :mod:`data_factory` so
  names never collide during parallel execution;
* **Negative assertions** — we assert access is *denied*, not just present;
* **Cleanup** — created projects are always deleted via the API in teardown.

WorkFlow Pro is fictional; tests skip cleanly until real credentials/endpoints
are configured through environment variables.
"""

from __future__ import annotations

from types import ModuleType

import pytest

from api.project_api import ProjectAPI
from config.config import Settings
from pages.dashboard_page import DashboardPage


@pytest.mark.tenant
@pytest.mark.regression
def test_company2_cannot_access_company1_project(
    company1_api: ProjectAPI,
    company2_api: ProjectAPI,
    project_factory: ModuleType,
    project_cleanup,
    settings: Settings,
) -> None:
    """Company 2 must be denied access to a project owned by Company 1."""
    if not (settings.is_api_configured and settings.secondary_credentials.api_token):
        pytest.skip("API tokens not configured (COMPANY1_API_TOKEN/COMPANY2_API_TOKEN).")

    # Step 1: Company 1 creates a project via API using UNIQUE test data.
    payload = project_factory.new_project_payload()
    project = company1_api.create_project(payload)
    project_id = project["id"]

    # Step 2: Register for cleanup immediately so teardown runs even on failure.
    project_cleanup(project_id)

    # Step 3: Company 1 CAN access its own project (positive control).
    assert company1_api.can_access_project(project_id) is True

    # Step 4: Company 2 must NOT access it — negative assertion (403/404).
    assert company2_api.can_access_project(project_id) is False


@pytest.mark.tenant
def test_user_role_is_enforced_in_ui(dashboard: DashboardPage, settings: Settings) -> None:
    """The dashboard reflects the signed-in user's tenant and role (RBAC)."""
    # Step 1: The `dashboard` fixture already logged in as the primary tenant.
    dashboard.expect_loaded()

    # Step 2: Validate the active tenant is Company 1 (isolation at the UI).
    dashboard.expect_tenant(settings.company1_tenant)

    # Step 3: Validate the role badge — the primary account is an admin here.
    dashboard.expect_role("admin")


@pytest.mark.tenant
def test_deleted_project_is_not_accessible(
    company1_api: ProjectAPI,
    project_factory: ModuleType,
    settings: Settings,
) -> None:
    """After deletion, even the owning tenant can no longer access the project."""
    if not settings.is_api_configured:
        pytest.skip("API token not configured (COMPANY1_API_TOKEN).")

    # Step 1: Create a uniquely-named project.
    payload = project_factory.new_project_payload()
    project = company1_api.create_project(payload)
    project_id = project["id"]

    # Step 2: Confirm it is accessible while it exists.
    assert company1_api.can_access_project(project_id) is True

    # Step 3: Delete it (explicit cleanup within the test body).
    company1_api.delete_project(project_id)

    # Step 4: Negative assertion — the project is gone (404 -> False).
    assert company1_api.can_access_project(project_id) is False
