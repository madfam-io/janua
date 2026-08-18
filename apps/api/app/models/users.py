"""Compatibility shim: ``app.models.users`` -> canonical ``app.models``.

The ``app.compliance.*`` package imports ``User`` from ``app.models.users``
(plural), but the model lives in ``app.models`` (``app/models/__init__.py``).
This mirrors the existing ``app.models.user`` (singular) backward-compat module
and unblocks the compliance imports without moving the model. New code should
import ``User`` from ``app.models`` directly.
"""

from app.models import Organization, OrganizationMember, Session, User, UserStatus

__all__ = ["User", "Session", "UserStatus", "Organization", "OrganizationMember"]
