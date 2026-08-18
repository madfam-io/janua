"""Compatibility shim: ``app.models.audit`` -> canonical ``app.models``.

The ``app.compliance.*`` package imports ``AuditLog`` from ``app.models.audit``,
but the model is actually defined in ``app.models`` (``app/models/__init__.py``).
The ``app.models.audit`` module never existed, contributing to the compliance
package being un-importable. This thin re-export fixes those imports without
moving the model or touching the importers. New code should import ``AuditLog``
from ``app.models`` directly.
"""

from app.models import AuditLog

__all__ = ["AuditLog"]
