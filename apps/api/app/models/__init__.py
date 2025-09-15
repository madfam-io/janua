"""
Models package for Plinto API

This package contains SQLAlchemy models for specialized features.
"""

# Import specialized models for easy access
from .sso import SSOConfiguration, SSOProvider, SSOStatus
from .compliance import ComplianceFramework, ComplianceCheck, ComplianceReport
from .enterprise import EnterpriseFeature, EnterpriseConfig, EnterpriseAudit
from .invitation import InvitationStatus, InvitationType, InvitationConfig
from .iot import IoTDevice, IoTDeviceType, IoTDeviceStatus
from .localization import LocaleConfig, TranslationKey, UserLocalePreference
from .migration import MigrationTask, MigrationStatus, MigrationConfig
from .policy import PolicyType, PolicyRule, PolicyEnforcement
from .white_label import WhiteLabelConfig, BrandingSettings, CustomDomain
from .zero_trust import ZeroTrustPolicy, TrustScore, SecurityContext

__all__ = [
    # SSO models
    'SSOConfiguration', 'SSOProvider', 'SSOStatus',

    # Compliance models
    'ComplianceFramework', 'ComplianceCheck', 'ComplianceReport',

    # Enterprise models
    'EnterpriseFeature', 'EnterpriseConfig', 'EnterpriseAudit',

    # Invitation models
    'InvitationStatus', 'InvitationType', 'InvitationConfig',

    # IoT models
    'IoTDevice', 'IoTDeviceType', 'IoTDeviceStatus',

    # Localization models
    'LocaleConfig', 'TranslationKey', 'UserLocalePreference',

    # Migration models
    'MigrationTask', 'MigrationStatus', 'MigrationConfig',

    # Policy models
    'PolicyType', 'PolicyRule', 'PolicyEnforcement',

    # White label models
    'WhiteLabelConfig', 'BrandingSettings', 'CustomDomain',

    # Zero trust models
    'ZeroTrustPolicy', 'TrustScore', 'SecurityContext',
]