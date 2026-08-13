"""
Policy and RBAC models with Pydantic schemas.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Additional SQLAlchemy models for Policy system
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String

from app.models.types import GUID as UUID
from app.models.types import JSON as JSONB

from . import Base

# Re-export SQLAlchemy models from __init__.py
from . import Policy as PolicyModel
from . import Role as RoleModel


class PolicyEffect(str, enum.Enum):
    """Policy effect enumeration."""

    ALLOW = "allow"
    DENY = "deny"


class PolicyTargetType(str, enum.Enum):
    """Policy target type enumeration."""

    USER = "user"
    ROLE = "role"
    ORGANIZATION = "organization"
    GLOBAL = "global"


class UserRole(Base):
    """User-Role assignment table."""

    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), index=True)
    scope = Column(String(50), default="organization")  # tenant, organization, global
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RolePolicy(Base):
    """Role-Policy association table."""

    __tablename__ = "role_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PolicyEvaluation(Base):
    """Policy evaluation results cache."""

    __tablename__ = "policy_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), index=True)  # user_id or role_id
    resource_type = Column(String(255))
    resource_id = Column(String(255))
    action = Column(String(255))
    result = Column(Boolean, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    context = Column(JSONB, default={})


# Pydantic Schemas


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    rules: Dict[str, Any] = Field(default_factory=dict)
    effect: PolicyEffect = PolicyEffect.ALLOW
    priority: int = Field(default=0, ge=0, le=1000)
    enabled: bool = True
    target_type: Optional[PolicyTargetType] = None
    target_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_pattern: Optional[str] = None
    actions: List[str] = Field(default_factory=list)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    organization_id: Optional[str] = Field(
        default=None,
        description=(
            "Owning organization. Optional when the caller belongs to exactly one "
            "organization; required otherwise. The caller must be a member of it."
        ),
    )


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None
    effect: Optional[PolicyEffect] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    enabled: Optional[bool] = None
    target_type: Optional[PolicyTargetType] = None
    target_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_pattern: Optional[str] = None
    actions: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class PolicyResponse(BaseModel):
    """Schema for policy response.

    `tenant_id` mirrors `organization_id` for wire compatibility, matching the
    convention `RoleResponse` already uses. `policies.tenant_id` does not exist;
    `organization_id` is the real tenancy column.
    """

    id: str
    tenant_id: str
    organization_id: Optional[str]
    name: str
    description: Optional[str]
    rules: Dict[str, Any]
    effect: str
    priority: int
    enabled: bool
    version: int
    target_type: Optional[str]
    target_id: Optional[str]
    resource_type: Optional[str]
    resource_pattern: Optional[str]
    actions: List[str]
    conditions: Dict[str, Any]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True

    @classmethod
    def from_orm(cls, obj):
        """Convert SQLAlchemy model to Pydantic schema.

        Every attribute read here is a real column on `app.models.Policy`. The
        previous `hasattr` guards on `enabled`/`version` silently degraded to
        defaults for columns that did not exist at all, which hid the drift
        instead of surfacing it.
        """
        organization_id = str(obj.organization_id) if obj.organization_id else None
        return cls(
            id=str(obj.id),
            tenant_id=organization_id or "",
            organization_id=organization_id,
            name=obj.name,
            description=obj.description,
            rules=obj.rules or {},
            effect=obj.effect,
            priority=obj.priority or 0,
            enabled=obj.enabled,
            version=obj.version,
            target_type=obj.target_type,
            target_id=obj.target_id,
            resource_type=obj.resource_type,
            resource_pattern=obj.resource_pattern,
            actions=obj.actions or [],
            conditions=obj.conditions or {},
            expires_at=obj.expires_at,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class PolicyEvaluateRequest(BaseModel):
    """Schema for policy evaluation request.

    The wire format is structured (`subject_id`, `resource_type`, `resource_id`),
    but `PolicyEngine` matches policies against flat `subject`/`resource`
    strings. The two derived properties below are that adapter. They used to be
    absent entirely, so `PolicyEngine.evaluate` raised `AttributeError` on
    `request.subject` before it issued a single query.
    """

    subject_id: Optional[str] = None  # user_id or role_id
    subject_type: str = Field(default="user", pattern="^(user|role)$")
    resource_type: str = Field(..., min_length=1)
    resource_id: Optional[str] = None
    action: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)

    @property
    def subject(self) -> str:
        """Flat subject identifier used for policy matching."""
        return self.subject_id or ""

    @property
    def resource(self) -> str:
        """Flat resource identifier, `type:id` when an id is supplied.

        Policy `resource_pattern`s are wildcard globs, so `documents:*` matches
        every document while `documents` still matches a type-only request.
        """
        if self.resource_id:
            return f"{self.resource_type}:{self.resource_id}"
        return self.resource_type


class PolicyEvaluateResponse(BaseModel):
    """Schema for policy evaluation response."""

    allowed: bool
    matched_policies: List[str] = Field(default_factory=list)
    denied_by: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoleCreate(BaseModel):
    """Schema for creating a role."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    organization_id: Optional[str] = None


class RoleResponse(BaseModel):
    """Schema for role response."""

    id: str
    tenant_id: str
    organization_id: Optional[str]
    name: str
    description: Optional[str]
    permissions: List[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True

    @classmethod
    def from_orm(cls, obj):
        """Convert SQLAlchemy model to Pydantic schema."""
        return cls(
            id=str(obj.id),
            tenant_id=str(obj.organization_id) if obj.organization_id else "",
            organization_id=str(obj.organization_id) if obj.organization_id else None,
            name=obj.name,
            description=obj.description,
            permissions=obj.permissions or [],
            is_system=obj.is_system if hasattr(obj, "is_system") else False,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


# Re-export SQLAlchemy models for convenience
Policy = PolicyModel
Role = RoleModel
