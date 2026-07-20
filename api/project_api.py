"""Project resource client for WorkFlow Pro.

Provides typed helpers for the project lifecycle used across the suite:
create → read → delete. Following the assessment's strategy, tests set up data
through this API (fast, reliable) and validate it through the UI, then clean up
through :meth:`ProjectAPI.delete_project`.
"""

from __future__ import annotations

import logging
from typing import Any

from api.base_api import APIError, BaseAPI

logger = logging.getLogger(__name__)

# NOTE: WorkFlow Pro is fictional and its real API contract is unavailable.
# The endpoint path below is an ASSUMPTION, deliberately isolated in this one
# constant so it can be reconciled with the real service in a single edit.
_PROJECTS = "/api/v1/projects"


class ProjectAPI(BaseAPI):
    """REST client for the ``/projects`` resource."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create_project(self, project: dict[str, Any]) -> dict[str, Any]:
        """Create a project and return the server representation.

        Parameters
        ----------
        project:
            Payload with at least ``name``; may include ``description``,
            ``members`` and ``status``.

        Returns
        -------
        dict
            The created project, including its server-assigned ``id``.
        """
        logger.info("Creating project via API: %s", project.get("name"))
        response = self.post(_PROJECTS, json=project)
        return response.json()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_project(self, project_id: str) -> dict[str, Any]:
        """Fetch a single project by ID."""
        logger.info("Fetching project %s", project_id)
        response = self.get(f"{_PROJECTS}/{project_id}")
        return response.json()

    def can_access_project(self, project_id: str) -> bool:
        """Return ``True`` if the current tenant can read ``project_id``.

        Used by isolation tests to assert that Company 2 receives a
        403/404 for Company 1's data instead of the record itself.
        """
        try:
            self.get(f"{_PROJECTS}/{project_id}")
            return True
        except APIError as exc:
            if exc.status_code in (401, 403, 404):
                logger.info(
                    "Access correctly denied for project %s (HTTP %s)",
                    project_id,
                    exc.status_code,
                )
                return False
            raise  # unexpected error — let the test see it

    # ------------------------------------------------------------------
    # Delete  (cleanup)
    # ------------------------------------------------------------------
    def delete_project(self, project_id: str) -> None:
        """Delete a project. Safe to call in teardown; logs but tolerates 404."""
        logger.info("Deleting project %s", project_id)
        try:
            self.delete(f"{_PROJECTS}/{project_id}")
        except APIError as exc:
            if exc.status_code == 404:
                logger.warning("Project %s already absent during cleanup", project_id)
                return
            raise
