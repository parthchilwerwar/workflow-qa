"""Centralised, environment-driven configuration for the WorkFlow Pro suite.

All runtime settings are read from environment variables (loaded from a local
``.env`` file during development, or injected as encrypted secrets in CI). No
credentials are ever hard-coded, mirroring the assessment assumption that
secrets live in CI secret storage and are never committed.

Two levels of checking are provided:

* :meth:`Settings.validate` raises :class:`ConfigurationError` for *malformed*
  configuration (bad browser name, non-positive timeout, non-HTTP URL). This is
  a hard error because the values are wrong, not merely absent.
* The ``is_*_configured`` properties report whether *optional* secrets are
  present. Tests use these to ``skip`` cleanly, because WorkFlow Pro is
  fictional and no real environment is available in this case study.

Usage
-----
>>> from config.config import get_settings
>>> settings = get_settings()
>>> settings.base_url
'https://app.workflowpro.example'
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

# Load variables from a local .env file if present. In CI the environment is
# already populated, so this is a no-op there.
load_dotenv()

# Browsers Playwright can drive; used to validate the BROWSER variable.
_SUPPORTED_BROWSERS = frozenset({"chromium", "firefox", "webkit"})


class ConfigurationError(RuntimeError):
    """Raised when configuration is present but malformed.

    Carries every problem found so the user can fix them all at once instead of
    re-running to discover the next error.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        bullet_list = "\n".join(f"  - {p}" for p in problems)
        super().__init__(
            "Invalid WorkFlow Pro configuration:\n"
            f"{bullet_list}\n"
            "Fix the environment variables above (see .env.example)."
        )


def _first_env(*names: str, default: str = "") -> str:
    """Return the first non-empty environment variable among ``names``.

    Supports migrating to new variable names while keeping older aliases
    working (e.g. ``COMPANY1_USERNAME`` with a ``TEST_USERNAME`` fallback).
    """
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _get_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable in a forgiving way."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int, *aliases: str) -> int:
    """Parse an integer environment variable, falling back to a default.

    A non-integer value is left as the sentinel ``-1`` so :meth:`Settings.validate`
    can surface a clear error rather than silently masking a typo.
    """
    raw = _first_env(name, *aliases)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return -1


@dataclass(frozen=True)
class TenantCredentials:
    """Immutable credential bundle for a single tenant/user."""

    tenant: str
    username: str
    password: str
    api_token: str = ""
    otp: str = ""

    @property
    def has_login(self) -> bool:
        """True when both a username and password are configured."""
        return bool(self.username and self.password)


@dataclass(frozen=True)
class Settings:
    """Strongly-typed view over all supported environment variables."""

    # --- Application under test ---------------------------------------
    base_url: str = field(
        default_factory=lambda: _first_env(
            "BASE_URL",
            "WORKFLOWPRO_BASE_URL",
            default="https://app.workflowpro.example",
        )
    )
    api_base_url: str = field(
        default_factory=lambda: _first_env(
            "API_BASE_URL",
            "WORKFLOWPRO_API_URL",
            default="https://api.workflowpro.example",
        )
    )
    test_env: str = field(default_factory=lambda: os.getenv("TEST_ENV", "staging"))

    # --- Browser / runtime --------------------------------------------
    headless: bool = field(default_factory=lambda: _get_bool("HEADLESS", True))
    browser: str = field(default_factory=lambda: os.getenv("BROWSER", "chromium").strip().lower())
    default_timeout: int = field(
        default_factory=lambda: _get_int("DEFAULT_TIMEOUT", 15_000, "TIMEOUT")
    )
    navigation_timeout: int = field(
        default_factory=lambda: _get_int("NAVIGATION_TIMEOUT", 30_000, "NAV_TIMEOUT")
    )

    # --- BrowserStack --------------------------------------------------
    use_browserstack: bool = field(default_factory=lambda: _get_bool("USE_BROWSERSTACK", False))
    browserstack_username: str = field(
        default_factory=lambda: os.getenv("BROWSERSTACK_USERNAME", "")
    )
    browserstack_access_key: str = field(
        default_factory=lambda: os.getenv("BROWSERSTACK_ACCESS_KEY", "")
    )

    # --- Primary tenant credentials (Company 1) -----------------------
    company1_tenant: str = field(default_factory=lambda: os.getenv("COMPANY1_TENANT", "company1"))
    company1_username: str = field(
        default_factory=lambda: _first_env("COMPANY1_USERNAME", "TEST_USERNAME")
    )
    company1_password: str = field(
        default_factory=lambda: _first_env("COMPANY1_PASSWORD", "TEST_PASSWORD")
    )
    company1_api_token: str = field(
        default_factory=lambda: _first_env("COMPANY1_API_TOKEN", "WORKFLOWPRO_API_TOKEN")
    )
    test_otp: str = field(default_factory=lambda: _first_env("TEST_OTP", "WORKFLOWPRO_TEST_OTP"))

    # --- Second tenant credentials (Company 2, isolation tests) -------
    company2_tenant: str = field(default_factory=lambda: os.getenv("COMPANY2_TENANT", "company2"))
    company2_username: str = field(default_factory=lambda: os.getenv("COMPANY2_USERNAME", ""))
    company2_password: str = field(default_factory=lambda: os.getenv("COMPANY2_PASSWORD", ""))
    company2_api_token: str = field(
        default_factory=lambda: _first_env("COMPANY2_API_TOKEN", "WORKFLOWPRO_API_TOKEN2")
    )

    # --- Derived helpers ----------------------------------------------
    @property
    def login_url(self) -> str:
        """Fully-qualified login page URL."""
        return f"{self.base_url.rstrip('/')}/login"

    @property
    def primary_credentials(self) -> TenantCredentials:
        """Credentials for the primary tenant (Company 1)."""
        return TenantCredentials(
            tenant=self.company1_tenant,
            username=self.company1_username,
            password=self.company1_password,
            api_token=self.company1_api_token,
            otp=self.test_otp,
        )

    @property
    def secondary_credentials(self) -> TenantCredentials:
        """Credentials for the second tenant (Company 2)."""
        return TenantCredentials(
            tenant=self.company2_tenant,
            username=self.company2_username,
            password=self.company2_password,
            api_token=self.company2_api_token,
        )

    # --- Configuration state (drives clean skips) ---------------------
    @property
    def is_ui_configured(self) -> bool:
        """True when the primary account can log into the web UI."""
        return self.primary_credentials.has_login

    @property
    def is_api_configured(self) -> bool:
        """True when the primary tenant has an API token."""
        return bool(self.primary_credentials.api_token)

    @property
    def has_second_tenant(self) -> bool:
        """True when Company 2 login credentials are configured."""
        return self.secondary_credentials.has_login

    @property
    def is_browserstack_configured(self) -> bool:
        """True when BrowserStack execution is requested and credentialled."""
        return bool(
            self.use_browserstack and self.browserstack_username and self.browserstack_access_key
        )

    # --- Validation of malformed values -------------------------------
    def validate(self) -> None:
        """Raise :class:`ConfigurationError` if any present value is malformed.

        Missing optional secrets are *not* an error here (tests skip cleanly);
        this only catches values that are set but wrong.
        """
        problems: list[str] = []

        if self.browser not in _SUPPORTED_BROWSERS:
            problems.append(
                f"BROWSER='{self.browser}' is not supported "
                f"(choose one of: {', '.join(sorted(_SUPPORTED_BROWSERS))})."
            )
        if self.default_timeout <= 0:
            problems.append("DEFAULT_TIMEOUT must be a positive integer (ms).")
        if self.navigation_timeout <= 0:
            problems.append("NAVIGATION_TIMEOUT must be a positive integer (ms).")
        for label, url in (("BASE_URL", self.base_url), ("API_BASE_URL", self.api_base_url)):
            if not url.startswith(("http://", "https://")):
                problems.append(f"{label}='{url}' must start with http:// or https://.")
        if self.use_browserstack and not (
            self.browserstack_username and self.browserstack_access_key
        ):
            problems.append(
                "USE_BROWSERSTACK is true but BROWSERSTACK_USERNAME / "
                "BROWSERSTACK_ACCESS_KEY are not both set."
            )

        if problems:
            raise ConfigurationError(problems)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, process-wide :class:`Settings` instance."""
    return Settings()
