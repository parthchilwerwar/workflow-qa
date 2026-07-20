"""Test-data factory for the WorkFlow Pro suite.

Generates *unique* payloads so tests stay independent and safe to run in
parallel. Tests should call these helpers instead of mutating the shared
``test-data/sample_project.json`` template (which is read-only reference data).

Example
-------
>>> from data_factory import new_project_payload
>>> payload = new_project_payload()
>>> payload["name"].startswith("qa-project-")
True
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_TEMPLATE_PATH = Path(__file__).parent / "test-data" / "sample_project.json"


def unique_suffix() -> str:
    """Return a collision-resistant suffix (UTC timestamp + short UUID)."""
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def load_template() -> dict[str, Any]:
    """Load the canonical sample project template from disk (a fresh copy)."""
    with _TEMPLATE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def new_project_payload(
    *,
    name_prefix: str = "qa-project",
    status: str = "active",
    members: list[dict[str, str]] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Build a valid, uniquely-named project payload.

    Parameters
    ----------
    name_prefix:
        Human-readable prefix; a unique suffix is always appended.
    status:
        Project status field.
    members:
        Optional member list; defaults to the template's members.
    description:
        Optional description; a generated one is used when omitted.
    """
    suffix = unique_suffix()
    template = load_template()
    return {
        "name": f"{name_prefix}-{suffix}",
        "description": description or f"Created by automated test run {suffix}",
        "status": status,
        "members": members if members is not None else template["members"],
        "metadata": template.get("metadata", {}),
    }


def invalid_project_payload(reason: str = "missing_name") -> dict[str, Any]:
    """Build a deliberately invalid payload for negative API tests.

    Parameters
    ----------
    reason:
        Which validation rule to violate:

        * ``"missing_name"`` — omit the required ``name`` field;
        * ``"blank_name"`` — send an empty ``name``;
        * ``"bad_status"`` — send an unrecognised ``status`` value.
    """
    base = new_project_payload()
    if reason == "missing_name":
        base.pop("name", None)
    elif reason == "blank_name":
        base["name"] = ""
    elif reason == "bad_status":
        base["status"] = "not-a-real-status"
    else:  # pragma: no cover - guard against typos in callers
        raise ValueError(f"Unknown invalid-payload reason: {reason!r}")
    return base
