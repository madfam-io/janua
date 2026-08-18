"""Compatibility shim: ``app.core.config`` -> canonical ``app.config``.

The ``app.compliance.*`` package historically imports settings from
``app.core.config``, but the project's canonical settings module is
``app.config`` (used by ~69 other modules). ``app.core.config`` never existed,
which made every ``app.compliance`` submodule (audit, incident, support,
dashboard, policies, privacy) fail to import — silently turning the compliance
privacy/data-subject handler into dead code.

This shim re-exports the settings surface from ``app.config`` so those modules
import cleanly, without touching their import statements or changing canonical
behavior. New code should import from ``app.config`` directly.
"""

from app.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
