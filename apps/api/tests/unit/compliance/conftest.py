"""
Compliance Tests conftest.py
Sets up mocks for compliance module dependencies before imports.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

# =============================================================================
# Mock problematic modules BEFORE any compliance imports
# This must happen at conftest load time (before test collection)
# =============================================================================

# Only set up mocks if they haven't been set up already
if "app.models.audit" not in sys.modules or isinstance(sys.modules.get("app.models.audit"), MagicMock):
    # Mock app.models.audit
    _mock_audit_model = MagicMock()
    _mock_audit_model.AuditLog = MagicMock()
    sys.modules["app.models.audit"] = _mock_audit_model

# Mock app.core.config if needed
if "app.core.config" not in sys.modules or isinstance(sys.modules.get("app.core.config"), MagicMock):
    _mock_config = MagicMock()
    _mock_config.settings = MagicMock()
    _mock_config.settings.DATABASE_URL = "postgresql://test:test@localhost/test"
    _mock_config.settings.SECRET_KEY = "test-secret-key"
    sys.modules["app.core.config"] = _mock_config

# Mock app.core.database if needed
if "app.core.database" not in sys.modules or isinstance(sys.modules.get("app.core.database"), MagicMock):
    _mock_database = MagicMock()
    _mock_database.get_session = MagicMock(return_value=AsyncMock())
    sys.modules["app.core.database"] = _mock_database
