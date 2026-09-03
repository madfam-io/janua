"""Fixtures shared across the router test modules.

`test_internal_users.py` owns the SQLite-backed provisioning fixtures; re-export
them here so sibling modules (e.g. `test_internal_users_identity_pool.py`) can
request them by name without importing — an imported fixture shadowed by a test
parameter trips ruff's F811.
"""

from test_internal_users import provisioning_client, provisioning_env  # noqa: F401
