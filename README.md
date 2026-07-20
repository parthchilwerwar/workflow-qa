# WorkFlow Pro — QA Automation Case Study

A test-automation framework built for the **WorkFlow Pro** QA Automation
Engineering take-home assessment. It demonstrates a layered Playwright + Pytest
architecture, a typed API client layer, multi-tenant isolation testing, a
mobile-emulation strategy, and a two-stage CI pipeline.

> **WorkFlow Pro is a fictional application and is not accessible.** This
> repository is *representative framework code*, not a working product test
> suite. No APIs are presented as real, no screenshots are fabricated, and no
> test run is presented as if executed against the live app. Where the
> application is unavailable, assumptions are documented explicitly (see
> [Assumptions](#assumptions)). Browser/API tests `skip` cleanly until real
> credentials and endpoints are supplied via environment variables; the pure
> unit tests run and pass locally today.

The original assessment brief is included at
[`docs/WorkFlow-Pro-Assessment.pdf`](docs/WorkFlow-Pro-Assessment.pdf).

---

## Table of Contents

- [Purpose](#purpose)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Architecture](#architecture)
- [Design Decisions](#design-decisions)
- [Assumptions](#assumptions)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Test Markers](#test-markers)
- [Mobile & BrowserStack Strategy](#mobile--browserstack-strategy)
- [Reporting & Diagnostics](#reporting--diagnostics)
- [CI/CD](#cicd)
- [Code Quality](#code-quality)
- [What Was Validated Locally](#what-was-validated-locally)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)

---

## Purpose

WorkFlow Pro is a multi-tenant SaaS project-management platform. The case study
covers three tracks:

1. **Fixing flaky login tests** — replacing timing-based assertions with
   web-first, retrying synchronisation on observable application state.
2. **Framework design** — a layered, maintainable architecture
   (tests → pages / API clients → fixtures → config).
3. **API + UI integration** — seeding data via API, validating through the UI
   on desktop and mobile viewports, and enforcing tenant isolation.

## Tech Stack

| Purpose            | Choice                                          |
| ------------------ | ----------------------------------------------- |
| Language           | Python 3.12+                                     |
| Browser automation | Playwright (sync API)                            |
| Test runner        | Pytest (`pytest-xdist`, `pytest-rerunfailures`, `pytest-html`) |
| API testing        | `requests`                                       |
| Configuration      | `python-dotenv` + environment variables          |
| Lint & format      | Ruff                                             |
| Cross-browser grid | BrowserStack (CDP connection, optional)          |
| CI/CD              | GitHub Actions                                   |

The framework defines its own `browser`/`context`/`page` fixtures against the
Playwright sync API, so the `pytest-playwright` plugin is intentionally **not**
a dependency.

## Repository Structure

```
workflowpro-qa-automation-case-study/
├── README.md
├── requirements.txt
├── pyproject.toml              # Ruff configuration
├── pytest.ini                  # pytest config + markers
├── conftest.py                 # root: sys.path + registers the fixture plugin
├── data_factory.py             # unique / invalid test-data generation
├── .gitignore
├── .env.example                # copy to .env for local runs
├── docs/
│   └── WorkFlow-Pro-Assessment.pdf
├── config/
│   ├── __init__.py
│   └── config.py               # env-driven, typed, validated settings
├── pages/                      # Page Object Model
│   ├── base_page.py
│   ├── login_page.py
│   ├── dashboard_page.py
│   └── projects_page.py
├── api/                        # REST client layer
│   ├── base_api.py
│   └── project_api.py
├── fixtures/
│   └── conftest.py             # browser/context/auth/API/cleanup/diagnostics
├── test-data/
│   └── sample_project.json     # read-only template (never mutated by tests)
├── tests/
│   ├── test_login.py
│   ├── test_multi_tenant_access.py
│   ├── test_project_creation_flow.py
│   └── test_unit_config_and_factory.py   # pure-logic tests (run & pass locally)
├── reports/
│   └── sample-test-report.md   # labelled EXAMPLE template, not a real run
└── .github/workflows/
    └── qa.yml
```

## Architecture

Four cooperating layers:

```
Test Layer (tests/)                 business behaviour, reads like a flow
        │ uses
Page Objects (pages/) + API Clients (api/)   UI encapsulation / backend calls
        │ built by
Fixtures (fixtures/conftest.py)     browser · context · auth · API · cleanup · diagnostics
        │ reads
Configuration (config/config.py)    env-driven, typed, validated
```

- **Tests** describe *what* is verified in business terms and stay independent.
- **Page objects** encapsulate UI interaction with stable locators and retrying
  assertions. `BasePage` holds only a small, curated set of reusable helpers.
- **API clients** centralise auth, timeouts, logging and error handling in a
  shared `BaseAPI`; `ProjectAPI` adds the project lifecycle used by the suite.
- **Fixtures** own the full setup/teardown lifecycle and diagnostics.
- **Configuration** is the single source of truth for every environment value.

## Design Decisions

- **Web-first, retrying assertions.** `expect(...)` and `page.wait_for_url(...)`
  instead of one-shot `is_visible()` or immediate URL equality — the root cause
  of the original flaky login tests. No `time.sleep` / `wait_for_timeout`.
- **Tolerant dashboard match.** Login waits on a regex that accepts trailing
  slashes, query params, and tenant sub-paths, then on a rendered marker.
- **ID-based verification.** Projects are validated by a stable
  `data-testid=project-card-<id>`, not by fragile visible text.
- **Centralised, validated config.** All values come from the environment.
  `Settings.validate()` raises a helpful `ConfigurationError` for *malformed*
  values (bad browser, non-positive timeout, non-HTTP URL); *missing* optional
  secrets cause a clean `skip` instead.
- **Unique test data.** `data_factory` generates UUID/timestamp-suffixed names
  so tests are independent and parallel-safe; the JSON template is never mutated.
- **Honest skips.** Because the app is fictional, environment-dependent tests
  `skip` (rather than fail) when configuration is absent.

## Assumptions

- A dedicated test environment and test accounts are available.
- Test users do not use real customer data.
- The Company 1 test account has 2FA disabled **or** supports a test-only OTP.
- Every tenant has a unique tenant ID/domain.
- The API supports creating, reading and deleting test projects.
- The web app exposes stable `data-testid` selectors.
- "Mobile" refers to the **responsive web app** on a mobile viewport. A native
  app would instead use Appium or BrowserStack App Automate.
- The API path (`/api/v1/projects`) is an **assumption**, isolated in a single
  constant in `api/project_api.py` to be reconciled with the real service.
- BrowserStack credentials are CI secrets and are never committed.

## Setup

```bash
# 1. Clone
git clone <your-fork-url> workflowpro-qa-automation-case-study
cd workflowpro-qa-automation-case-study

# 2. Create and activate a virtual environment (Python 3.12+)
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install the Playwright browser binary (required for UI tests)
python -m playwright install --with-deps chromium

# 5. Configure environment
cp .env.example .env      # then edit .env with real values
```

## Environment Variables

Copy `.env.example` to `.env`. All values are read through `config/config.py`.

| Variable                  | Purpose                                             |
| ------------------------- | --------------------------------------------------- |
| `BASE_URL`                | Web application base URL                             |
| `API_BASE_URL`            | REST API base URL                                    |
| `TEST_ENV`                | Free-form environment label (e.g. `staging`, `ci`)  |
| `BROWSER`                 | `chromium` \| `firefox` \| `webkit`                  |
| `HEADLESS`                | `true` / `false`                                     |
| `DEFAULT_TIMEOUT`         | Default action timeout (ms)                          |
| `NAVIGATION_TIMEOUT`      | Default navigation timeout (ms)                      |
| `COMPANY1_USERNAME` / `COMPANY1_PASSWORD` | Primary tenant login             |
| `COMPANY1_API_TOKEN`      | Primary tenant API bearer token                      |
| `TEST_OTP`                | Test-only OTP (blank if 2FA disabled)                |
| `COMPANY2_USERNAME` / `COMPANY2_PASSWORD` | Second tenant login (isolation)  |
| `COMPANY2_API_TOKEN`      | Second tenant API bearer token                       |
| `COMPANY1_TENANT` / `COMPANY2_TENANT` | Tenant identifiers                     |
| `USE_BROWSERSTACK`        | `true` to route the browser to BrowserStack          |
| `BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY` | Grid credentials       |

`TEST_USERNAME` / `TEST_PASSWORD` are accepted as aliases for the `COMPANY1_*`
login credentials when you prefer generic names for a single-tenant smoke test.

## Running Tests

```bash
# Everything (unit tests run; env-dependent tests skip without config)
pytest

# Just the pure-logic unit tests (no browser, no network)
pytest -m unit

# By marker
pytest -m smoke
pytest -m tenant
pytest -m "integration and mobile"

# Parallel + retry (as in CI)
pytest -n auto --reruns 1

# Self-contained HTML report
pytest --html=reports/report.html --self-contained-html
```

> Without a configured environment, browser/API tests **skip** with a clear
> message rather than fail — the app is fictional and intentionally inaccessible.

## Test Markers

Registered in `pytest.ini`:

| Marker        | Scope                                                  |
| ------------- | ------------------------------------------------------ |
| `smoke`       | Fast, critical-path checks for every commit            |
| `regression`  | Broader coverage for scheduled / pre-release runs      |
| `login`       | Authentication, 2FA handling, session readiness        |
| `tenant`      | Tenant isolation and role-based access control         |
| `integration` | End-to-end API-setup + UI-validation flows             |
| `mobile`      | Responsive validation on emulated mobile viewports     |
| `api`         | Pure API-layer tests (no browser)                      |
| `unit`        | Pure-logic tests (no browser, no network)              |

## Mobile & BrowserStack Strategy

The framework separates three execution modes, all driven by configuration:

- **Local Chromium** — the default `context` fixture (desktop viewport).
- **Responsive mobile emulation** — the `mobile_context` fixture emulates a
  phone viewport with touch, used by the integration flow. No cloud account
  needed.
- **Optional BrowserStack** — when `USE_BROWSERSTACK=true` *and* credentials are
  present, the `browser` fixture connects over CDP to the BrowserStack grid; the
  rest of the framework is identical. If BrowserStack is requested but not
  credentialled, `Settings.validate()` raises a clear error rather than
  silently reporting a pass. For a **native** app the strategy would switch to
  Appium / BrowserStack App Automate (out of scope here).

## Reporting & Diagnostics

- **HTML report** via `pytest-html` (`reports/report.html`).
- **JUnit XML** (`reports/junit.xml`) for CI dashboards.
- **Screenshot on failure** — captured automatically for tests using a page.
- **Playwright trace on failure** — each context records a trace and saves it to
  `traces/` only when the test fails.
- **Logs** — readable `log_cli` output during runs.

All generated runtime artifacts (`reports/report.html`, `reports/*.xml`,
`screenshots/`, `traces/`, `videos/`) are git-ignored. The committed
`reports/sample-test-report.md` is clearly labelled as an **example template**,
not a real execution result.

## CI/CD

Defined in [`.github/workflows/qa.yml`](.github/workflows/qa.yml) as two jobs:

1. **`static-checks`** — needs no credentials, runs on every push/PR:
   `ruff check`, `ruff format --check`, `compileall`, and `pytest --collect-only`.
2. **`tests`** — installs the Playwright browser and runs the suite with
   `-n auto --reruns 1`, uploading reports/screenshots/traces on **every** run
   (including failures) and publishing a JUnit summary.

All application/BrowserStack credentials are injected as encrypted GitHub
secrets. Because environment-dependent tests skip cleanly, the pipeline does
**not** fail merely because private credentials are unavailable, and it never
runs fictional end-to-end tests against an unreachable URL.

## Code Quality

- **Ruff** for linting and formatting, configured in `pyproject.toml`
  (pycodestyle, pyflakes, isort, pyupgrade, bugbear, comprehensions, simplify).
- Consistent type hints, docstrings, and `from __future__ import annotations`.
- No `pass`/`TODO`/`...` placeholders and no fabricated output.

## What Was Validated Locally

Run on Windows with Python 3.14 (target runtime is 3.12+):

| Check                                   | Result                              |
| --------------------------------------- | ----------------------------------- |
| `python -m compileall ...`              | Pass — all modules compile          |
| `ruff check .`                          | Pass — no lint errors               |
| `ruff format --check .`                 | Pass — 19 files formatted           |
| `pytest --collect-only`                 | Pass — 18 tests collected           |
| `pytest -m unit`                        | **11 passed**                       |
| `pytest` (full)                         | 11 passed, 7 skipped (env absent)   |

The 7 skips are the browser/API tests, which require a real environment.

## Limitations

- WorkFlow Pro is **fictional and inaccessible**. The browser/API tests are
  representative and have **not** been executed against a live application; no
  execution output is fabricated.
- Selector names (`data-testid` values), the API path (`/api/v1/projects`), and
  role labels are assumptions to be reconciled with the real application.
- Full execution (login, tenant isolation, integration) requires a real test
  environment plus the credentials listed under
  [Environment Variables](#environment-variables) and an installed Playwright
  browser.

## Future Improvements

- Contract tests against the real API schema once available.
- Visual regression checks for key screens.
- Parameterise the full RBAC matrix (admin/member/viewer) across UI + API.
- A BrowserStack job matrix across Chromium/Firefox/WebKit.
- Add `mypy` once the type surface is complete enough to be strict.

---

**Author:** Parth Chilwerwar · `job.parthchilwerwar@gmail.com`
