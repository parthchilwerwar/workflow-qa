# Sample Test Execution Report

> **Note:** WorkFlow Pro is a fictional application and was **not** accessible
> during this assessment. This report is a **representative sample** of the
> output the framework produces (it mirrors the `pytest-html` summary and the
> JUnit XML uploaded as a CI artifact). It is **not** a record of a real run
> against the target application. When run against a configured environment,
> these numbers are generated automatically.

---

## Execution Summary

| Metric              | Value                                    |
| ------------------- | ---------------------------------------- |
| Suite               | WorkFlow Pro – QA Automation Case Study  |
| Environment         | `staging` (representative)               |
| Browser             | Chromium 129 (Playwright)                |
| Grid                | BrowserStack (Windows 11)                |
| Total tests         | 7                                        |
| Passed              | 6                                        |
| Failed              | 1                                        |
| Skipped             | 0                                        |
| Total execution time| 48.3s                                    |
| Parallel workers    | 2 (`pytest -n auto`)                     |
| Retries used        | 1 (via `pytest-rerunfailures`)           |

---

## Passed Tests

| Test                                                             | Marker(s)            | Time   |
| ---------------------------------------------------------------- | -------------------- | ------ |
| `test_login.py::test_successful_login_reaches_dashboard`         | smoke, login         | 6.1s   |
| `test_login.py::test_invalid_credentials_show_error`             | login                | 3.4s   |
| `test_login.py::test_login_helper_is_idempotent`                 | login                | 5.7s   |
| `test_multi_tenant_access.py::test_company2_cannot_access_...`   | tenant, regression   | 4.9s   |
| `test_multi_tenant_access.py::test_user_role_is_enforced_in_ui`  | tenant               | 5.2s   |
| `test_multi_tenant_access.py::test_deleted_project_is_not_...`   | tenant               | 3.8s   |

---

## Failed Tests

| Test                                                        | Marker(s)          | Time   |
| ----------------------------------------------------------- | ------------------ | ------ |
| `test_project_creation_flow.py::test_project_creation_flow` | integration, mobile| 19.2s  |

**Representative failure detail**

```
AssertionError: project card not visible on mobile viewport within 15000ms
  locator: get_by_test_id("project-card-8f3a2c1e")
  where:   mobile_context (390x844)

Captured evidence:
  screenshots/test_project_creation_flow-20260721-010512.png
  traces/test_project_creation_flow.zip
```

**Interpretation:** the project was created and validated on desktop, but the
mobile layout rendered the projects list lazily beyond the default timeout.
Recommended follow-up: assert on the list container readiness marker before the
card, and raise the mobile navigation timeout. (Illustrative only.)

---

## Environment Details

| Setting            | Value                              |
| ------------------ | ---------------------------------- |
| `BASE_URL`         | `https://app.workflowpro.example`  |
| `API_BASE_URL`     | `https://api.workflowpro.example`  |
| `TEST_ENV`         | `staging`                          |
| `HEADLESS`         | `true`                             |
| `BROWSER`          | `chromium`                         |
| `DEFAULT_TIMEOUT`  | `15000` ms                         |
| `NAVIGATION_TIMEOUT`| `30000` ms                        |
| Python             | `3.12`                             |
| Playwright         | `1.48.0`                           |
| pytest             | `8.3.3`                            |
| OS (runner)        | `ubuntu-latest` / BrowserStack Win 11 |

---

## Artifacts

- `reports/report.html` — self-contained HTML report (`pytest-html`)
- `reports/junit.xml` — JUnit results for CI dashboards
- `screenshots/*.png` — automatic capture on failure
- `traces/*.zip` — Playwright traces for post-mortem debugging
