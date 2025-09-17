"""
Plinto Alert System
Comprehensive alerting system with modular components for evaluation, notification, and management
"""

# Import all public interfaces for backwards compatibility
from .models import (
    AlertSeverity,
    AlertStatus,
    AlertChannel,
    AlertRule,
    Alert,
    NotificationChannel,
    EvaluationResult
)

from .evaluation.evaluator import AlertEvaluator
from .notification.sender import NotificationSender
from .metrics import MetricsCollector, metrics_collector
from .manager import AlertManager, alert_manager

# Maintain backwards compatibility with original single-file interface
__all__ = [
    # Models
    "AlertSeverity",
    "AlertStatus",
    "AlertChannel",
    "AlertRule",
    "Alert",
    "NotificationChannel",
    "EvaluationResult",

    # Core components
    "AlertEvaluator",
    "NotificationSender",
    "MetricsCollector",
    "AlertManager",

    # Global instances
    "alert_manager",
    "metrics_collector"
]

# For complete backwards compatibility, expose the main manager instance
# as if it were the original AlertSystem class
AlertSystem = AlertManager