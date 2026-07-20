"""Base page object shared by every page in the WorkFlow Pro suite.

Design notes
------------
* Every concrete page inherits from :class:`BasePage` and receives the active
  Playwright :class:`~playwright.sync_api.Page`.
* Prefer **retrying, web-first assertions** (``expect(...)``) and role/test-id
  locators over brittle CSS selectors — this directly addresses the flaky-test
  problems described in the assessment (race conditions and non-retrying
  ``is_visible()`` checks).
* Common, reusable interactions live here so page objects stay small and
  focused on their own domain.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Locator, Page, expect

logger = logging.getLogger(__name__)


class BasePage:
    """Foundation for all page objects.

    Parameters
    ----------
    page:
        The Playwright page bound to the current browser context.
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None:
        """Navigate to ``url`` and wait for a deterministic load state.

        We wait for ``domcontentloaded`` rather than a fixed sleep so the test
        synchronises on an observable browser state instead of timing.
        """
        logger.info("Navigating to %s", url)
        self.page.goto(url, wait_until=wait_until)

    # ------------------------------------------------------------------
    # Locator helpers  (test-id first, then role, then label)
    # ------------------------------------------------------------------
    def by_test_id(self, test_id: str) -> Locator:
        """Return a locator for a stable ``data-testid`` attribute."""
        return self.page.get_by_test_id(test_id)

    def by_role(self, role: str, name: str | None = None) -> Locator:
        """Return an accessibility-role based locator."""
        if name is not None:
            return self.page.get_by_role(role, name=name)  # type: ignore[arg-type]
        return self.page.get_by_role(role)  # type: ignore[arg-type]

    def by_label(self, text) -> Locator:
        """Return a locator matched by its associated form label."""
        return self.page.get_by_label(text)

    # ------------------------------------------------------------------
    # Actions  (thin, logged wrappers around Playwright)
    # ------------------------------------------------------------------
    def click(self, locator: Locator) -> None:
        """Click a locator; Playwright auto-waits for it to be actionable."""
        locator.click()

    def fill(self, locator: Locator, value: str) -> None:
        """Fill an input; ``fill`` clears and waits for editability."""
        locator.fill(value)

    # ------------------------------------------------------------------
    # Assertions  (retrying / web-first)
    # ------------------------------------------------------------------
    def expect_visible(self, locator: Locator, *, timeout: int | None = None) -> None:
        """Assert a locator becomes visible, retrying until the timeout."""
        expect(locator).to_be_visible(timeout=timeout)

    def expect_hidden(self, locator: Locator, *, timeout: int | None = None) -> None:
        """Assert a locator is absent/hidden, retrying until the timeout."""
        expect(locator).to_be_hidden(timeout=timeout)

    def expect_text(self, locator: Locator, text: str, *, timeout: int | None = None) -> None:
        """Assert a locator contains the expected text (retrying)."""
        expect(locator).to_contain_text(text, timeout=timeout)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def screenshot(self, path: str, *, full_page: bool = True) -> None:
        """Capture a screenshot for failure evidence."""
        self.page.screenshot(path=path, full_page=full_page)

    @property
    def current_url(self) -> str:
        """Return the browser's current URL."""
        return self.page.url
