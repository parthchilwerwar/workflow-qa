"""Base HTTP API client for WorkFlow Pro.

Wraps :mod:`requests` with a shared session, per-tenant authentication,
structured logging and consistent error handling. Concrete clients (e.g.
:class:`~api.project_api.ProjectAPI`) inherit from :class:`BaseAPI`.

Why a thin custom client instead of raw ``requests`` calls in tests?
* centralises auth headers and the base URL;
* gives every request/response the same logging for failure triage;
* converts non-2xx responses into a typed :class:`APIError` so tests fail with
  a meaningful message instead of a bare status code.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Reasonable default so a hung backend never blocks CI indefinitely.
DEFAULT_TIMEOUT = 30  # seconds


class APIError(RuntimeError):
    """Raised when the API returns an unexpected (non-2xx) response."""

    def __init__(self, method: str, url: str, status_code: int, body: str) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.body = body
        super().__init__(f"{method} {url} failed with HTTP {status_code}: {body[:500]}")


class BaseAPI:
    """Shared behaviour for all REST clients.

    Parameters
    ----------
    base_url:
        Root URL of the API (e.g. ``https://api.workflowpro.com``).
    token:
        Bearer token used for authentication. Scoped per tenant so isolation
        tests can instantiate one client per company.
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        token: str = "",
        *,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

    # ------------------------------------------------------------------
    # Low-level request plumbing
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        """Join the base URL with an endpoint path."""
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        expected_status: tuple[int, ...] = (200, 201, 204),
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an HTTP request with logging and status validation.

        Parameters
        ----------
        method:
            HTTP verb, e.g. ``"GET"``.
        path:
            Endpoint path relative to the base URL.
        expected_status:
            Status codes considered successful for this call.
        **kwargs:
            Forwarded to :meth:`requests.Session.request` (``json``,
            ``params``, ``headers`` ...).

        Raises
        ------
        APIError
            If the response status is not in ``expected_status``.
        """
        url = self._url(path)
        kwargs.setdefault("timeout", self.timeout)
        logger.info("API %s %s", method, url)

        try:
            response = self._session.request(method, url, **kwargs)
        except requests.RequestException as exc:  # network / DNS / timeout
            logger.error("API request error: %s %s -> %s", method, url, exc)
            raise APIError(method, url, status_code=0, body=str(exc)) from exc

        if response.status_code not in expected_status:
            logger.error("Unexpected status %s for %s %s", response.status_code, method, url)
            raise APIError(method, url, response.status_code, response.text)

        logger.debug("API %s %s -> %s", method, url, response.status_code)
        return response

    # ------------------------------------------------------------------
    # Convenience verbs
    # ------------------------------------------------------------------
    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, expected_status=(200,), **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, expected_status=(200, 201), **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, expected_status=(200, 202, 204), **kwargs)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
