"""Reusable pytest fixtures for the WorkFlow Pro automation framework.

Provides the full setup/teardown backbone used by every test:

* **configuration** – typed :class:`~config.config.Settings`, validated once;
* **browser / context / page** – Playwright lifecycle, local or BrowserStack;
* **authentication** – logged-in page + ready dashboard;
* **API clients** – per-tenant :class:`~api.project_api.ProjectAPI`;
* **test data** – a :mod:`data_factory` accessor for unique payloads;
* **cleanup** – a registry that deletes created projects after each test;
* **diagnostics** – screenshots and Playwright traces captured on failure.

Registered as a plugin from the repository-root ``conftest.py``.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

import data_factory
from api.project_api import ProjectAPI
from config.config import Settings, TenantCredentials, get_settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage

logger = logging.getLogger(__name__)

# Directories for runtime artifacts (created lazily; ignored by git).
_SCREENSHOT_DIR = Path("screenshots")
_TRACE_DIR = Path("traces")
_TEST_DATA_DIR = Path("test-data")

# Viewports kept in one place instead of scattered magic numbers.
_DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
_MOBILE_VIEWPORT = {"width": 390, "height": 844}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def settings() -> Settings:
    """Session-wide configuration, validated once for malformed values."""
    config = get_settings()
    config.validate()  # raises ConfigurationError with a helpful message
    return config


@pytest.fixture(scope="session")
def sample_project_data() -> dict[str, Any]:
    """Read-only sample project template loaded from test-data/."""
    path = _TEST_DATA_DIR / "sample_project.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def project_factory() -> ModuleType:
    """Expose the test-data factory for generating unique payloads per test."""
    return data_factory


# ---------------------------------------------------------------------------
# Playwright lifecycle: playwright -> browser -> context -> page
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def playwright() -> Iterator[Playwright]:
    """Start/stop the Playwright driver once per session."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright: Playwright, settings: Settings) -> Iterator[Browser]:
    """Launch a browser locally, or connect to BrowserStack when enabled.

    WorkFlow Pro is fictional, so every UI test needs a real, configured
    environment. When primary credentials are absent we ``skip`` here (a
    session-scoped skip) so all browser-dependent tests skip *cleanly* instead
    of erroring on a browser launch or navigating to a non-existent host.
    """
    if not settings.is_ui_configured:
        pytest.skip(
            "UI tests require a configured environment — set COMPANY1_USERNAME "
            "and COMPANY1_PASSWORD (and a reachable BASE_URL) to run them."
        )

    if settings.use_browserstack:
        logger.info("Connecting to BrowserStack grid")
        caps = {
            "browser": settings.browser,
            "os": "Windows",
            "os_version": "11",
            "name": f"WorkFlow Pro {settings.test_env} run",
            "build": os.getenv("GITHUB_RUN_ID", "local-build"),
            "browserstack.username": settings.browserstack_username,
            "browserstack.accessKey": settings.browserstack_access_key,
        }
        endpoint = "wss://cdp.browserstack.com/playwright?caps=" + json.dumps(caps)
        browser = playwright.chromium.connect_over_cdp(endpoint)
    else:
        browser_type = getattr(playwright, settings.browser)
        browser = browser_type.launch(headless=settings.headless)

    try:
        yield browser
    finally:
        browser.close()


def _new_context(
    browser: Browser, settings: Settings, viewport: dict[str, int], *, mobile: bool
) -> BrowserContext:
    """Create a context with timeouts applied and tracing started."""
    ctx = browser.new_context(
        viewport=viewport,
        is_mobile=mobile,
        has_touch=mobile,
        device_scale_factor=3 if mobile else 1,
    )
    ctx.set_default_timeout(settings.default_timeout)
    ctx.set_default_navigation_timeout(settings.navigation_timeout)
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    return ctx


def _finalize_context(ctx: BrowserContext, request: Any, label: str) -> None:
    """Save a Playwright trace when the test failed, then close the context."""
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:
        _TRACE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = request.node.name.replace("/", "_").replace("::", "_")
        target = _TRACE_DIR / f"{safe_name}-{label}-{stamp}.zip"
        try:
            ctx.tracing.stop(path=str(target))
            logger.error("Saved failure trace: %s", target)
        except Exception as exc:  # noqa: BLE001 - never fail teardown
            logger.warning("Could not save trace: %s", exc)
            ctx.tracing.stop()
    else:
        ctx.tracing.stop()
    ctx.close()


@pytest.fixture
def context(browser: Browser, settings: Settings, request: Any) -> Iterator[BrowserContext]:
    """Fresh, isolated desktop context per test (with tracing)."""
    ctx = _new_context(browser, settings, _DESKTOP_VIEWPORT, mobile=False)
    try:
        yield ctx
    finally:
        _finalize_context(ctx, request, "desktop")


@pytest.fixture
def mobile_context(browser: Browser, settings: Settings, request: Any) -> Iterator[BrowserContext]:
    """Mobile-emulating context for responsive validation (with tracing)."""
    ctx = _new_context(browser, settings, _MOBILE_VIEWPORT, mobile=True)
    try:
        yield ctx
    finally:
        _finalize_context(ctx, request, "mobile")


@pytest.fixture
def page(context: BrowserContext) -> Iterator[Page]:
    """A single page for the current test."""
    pg = context.new_page()
    try:
        yield pg
    finally:
        pg.close()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _login_with(page: Page, settings: Settings, creds: TenantCredentials) -> Page:
    """Perform a reliable login and return the authenticated page."""
    if not creds.has_login:
        pytest.skip(
            "Credentials not configured — set COMPANY1_USERNAME/PASSWORD "
            "(and COMPANY2_* for the second tenant) to run authenticated tests."
        )
    LoginPage(page).login(
        settings.login_url,
        creds.username,
        creds.password,
        otp=creds.otp or None,
        nav_timeout=settings.navigation_timeout,
        dashboard_timeout=settings.default_timeout,
    )
    return page


@pytest.fixture
def authenticated_page(page: Page, settings: Settings) -> Page:
    """A page already logged in as the primary tenant (Company 1)."""
    return _login_with(page, settings, settings.primary_credentials)


@pytest.fixture
def dashboard(authenticated_page: Page) -> DashboardPage:
    """Ready dashboard page object for the primary tenant."""
    dash = DashboardPage(authenticated_page)
    dash.expect_loaded()
    return dash


# ---------------------------------------------------------------------------
# API clients (one per tenant, for isolation testing)
# ---------------------------------------------------------------------------
@pytest.fixture
def company1_api(settings: Settings) -> Iterator[ProjectAPI]:
    """Project API client authenticated as the primary tenant."""
    client = ProjectAPI(settings.api_base_url, settings.primary_credentials.api_token)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def company2_api(settings: Settings) -> Iterator[ProjectAPI]:
    """Project API client authenticated as the second tenant."""
    client = ProjectAPI(settings.api_base_url, settings.secondary_credentials.api_token)
    try:
        yield client
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Cleanup registry
# ---------------------------------------------------------------------------
@pytest.fixture
def project_cleanup(company1_api: ProjectAPI) -> Iterator[Callable[[str], None]]:
    """Register created project IDs and delete them after the test.

    Yields a ``register(project_id)`` callable. Teardown runs even if the test
    fails, so no orphaned test data is left behind.
    """
    created: list[str] = []

    def register(project_id: str) -> None:
        created.append(project_id)

    try:
        yield register
    finally:
        for project_id in created:
            try:
                company1_api.delete_project(project_id)
            except Exception as exc:  # noqa: BLE001 - never fail teardown
                logger.warning("Cleanup failed for project %s: %s", project_id, exc)


# ---------------------------------------------------------------------------
# Diagnostics: screenshots on failure  (pytest report hook + helper)
# ---------------------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # type: ignore[no-untyped-def]
    """Expose each phase's report on the item for the diagnostics fixtures."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def _screenshot_on_failure(request: Any) -> Iterator[None]:
    """Capture a full-page screenshot when a test using a page fails."""
    yield
    report = getattr(request.node, "rep_call", None)
    if report is None or not report.failed:
        return

    page_obj: Page | None = None
    for name in ("authenticated_page", "page"):
        if name in request.fixturenames:
            candidate = request.getfixturevalue(name)
            if isinstance(candidate, Page):
                page_obj = candidate
                break
    if page_obj is None:
        return

    _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = request.node.name.replace("/", "_").replace("::", "_")
    target = _SCREENSHOT_DIR / f"{safe_name}-{stamp}.png"
    try:
        page_obj.screenshot(path=str(target), full_page=True)
        logger.error("Saved failure screenshot: %s", target)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not capture screenshot: %s", exc)
