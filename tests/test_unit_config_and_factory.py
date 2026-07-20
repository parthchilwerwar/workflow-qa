"""Pure-logic unit tests — no browser, no network, no external app.

These exercise the parts of the framework that can be validated locally right
now: the configuration layer (validation + env-var aliasing) and the test-data
factory (uniqueness, template immutability, invalid payloads). They run and
pass without any WorkFlow Pro environment, which is why the case study is not
entirely skip-only.
"""

from __future__ import annotations

import pytest

import data_factory
from config.config import ConfigurationError, Settings


# ---------------------------------------------------------------------------
# Data factory
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_new_project_payload_is_unique() -> None:
    """Two payloads must have distinct, prefixed names and required fields."""
    first = data_factory.new_project_payload()
    second = data_factory.new_project_payload()

    assert first["name"] != second["name"]
    assert first["name"].startswith("qa-project-")
    assert first["status"] == "active"
    assert {"name", "description", "status", "members"} <= set(first)


@pytest.mark.unit
def test_factory_does_not_mutate_template() -> None:
    """Mutating a generated payload must not affect the on-disk template."""
    payload = data_factory.new_project_payload()
    payload["members"].append({"email": "x@y.test", "role": "admin"})

    fresh_template = data_factory.load_template()
    assert len(fresh_template["members"]) < len(payload["members"])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("reason", "check"),
    [
        ("missing_name", lambda p: "name" not in p),
        ("blank_name", lambda p: p["name"] == ""),
        ("bad_status", lambda p: p["status"] == "not-a-real-status"),
    ],
)
def test_invalid_payloads(reason: str, check) -> None:
    """Each invalid-payload variant violates exactly the intended rule."""
    assert check(data_factory.invalid_project_payload(reason))


@pytest.mark.unit
def test_invalid_payload_unknown_reason_raises() -> None:
    """An unknown reason is a programming error and must fail loudly."""
    with pytest.raises(ValueError):
        data_factory.invalid_project_payload("nonsense")


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------
@pytest.mark.unit
def test_default_configuration_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults (placeholder URLs, chromium, positive timeouts) must validate."""
    for var in ("BROWSER", "DEFAULT_TIMEOUT", "NAVIGATION_TIMEOUT", "BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    Settings().validate()  # should not raise


@pytest.mark.unit
def test_invalid_browser_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unsupported BROWSER value raises a helpful ConfigurationError."""
    monkeypatch.setenv("BROWSER", "safari")
    with pytest.raises(ConfigurationError) as exc:
        Settings().validate()
    assert "BROWSER" in str(exc.value)


@pytest.mark.unit
def test_non_integer_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-integer timeout is surfaced instead of being silently ignored."""
    monkeypatch.setenv("DEFAULT_TIMEOUT", "not-a-number")
    with pytest.raises(ConfigurationError) as exc:
        Settings().validate()
    assert "DEFAULT_TIMEOUT" in str(exc.value)


@pytest.mark.unit
def test_credential_alias_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """TEST_USERNAME/PASSWORD act as aliases for COMPANY1_* when set."""
    monkeypatch.delenv("COMPANY1_USERNAME", raising=False)
    monkeypatch.delenv("COMPANY1_PASSWORD", raising=False)
    monkeypatch.setenv("TEST_USERNAME", "alias.user@company1.test")
    monkeypatch.setenv("TEST_PASSWORD", "alias-pass")

    settings = Settings()
    assert settings.is_ui_configured is True
    assert settings.primary_credentials.username == "alias.user@company1.test"


@pytest.mark.unit
def test_configuration_state_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """The is_*_configured helpers reflect which secrets are present."""
    for var in (
        "COMPANY1_USERNAME",
        "COMPANY1_PASSWORD",
        "COMPANY1_API_TOKEN",
        "TEST_USERNAME",
        "TEST_PASSWORD",
        "WORKFLOWPRO_API_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)

    assert Settings().is_ui_configured is False
    assert Settings().is_api_configured is False

    monkeypatch.setenv("COMPANY1_API_TOKEN", "token-123")
    assert Settings().is_api_configured is True
