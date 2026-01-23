"""
Alerting Package
Modular alerting system with separated concerns for evaluation, notification, and management.
"""

from .alert_system_refactored import (
    alert_manager,
    get_alert_health,
    initialize_alerting,
    trigger_manual_alert,
)
from .core import (
    Alert,
    AlertChannel,
    AlertEvaluator,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
    NotificationSender,
)

__all__ = [
    "AlertSeverity",
    "AlertStatus",
    "AlertChannel",
    "AlertRule",
    "Alert",
    "NotificationChannel",
    "AlertEvaluator",
    "NotificationSender",
    "AlertManager",
    "alert_manager",
    "initialize_alerting",
    "trigger_manual_alert",
    "get_alert_health",
]
