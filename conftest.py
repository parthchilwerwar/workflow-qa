"""Repository-root pytest configuration.

Two responsibilities only:

1. Ensure the project root is importable so ``config``, ``pages``, ``api`` and
   ``fixtures`` resolve regardless of where pytest is invoked from.
2. Register ``fixtures/conftest.py`` as a plugin so all shared fixtures and the
   screenshot-on-failure hook are available to every test.

``pytest_plugins`` must live in the top-level conftest, which is why this thin
file exists alongside the richer ``fixtures/conftest.py``.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load the shared fixture library as a plugin.
pytest_plugins = ["fixtures.conftest"]
