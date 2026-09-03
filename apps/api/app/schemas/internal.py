"""
Schemas for internal service-to-service API endpoints.
Used by hub services (Dhanam, etc.) to sync state with Janua.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TierSyncRequest(BaseModel):
    """Request to sync an organization's subscription tier from Dhanam."""

    tier: Literal["free_tier", "pro_tier", "scale_tier", "enterprise_tier"]
    source: str = "dhanam"
    idempotency_key: str


class TierSyncResponse(BaseModel):
    """Response after syncing an organization's subscription tier."""

    status: str
    previous_tier: Optional[str] = None
    new_tier: str


class ProvisionUserRequest(BaseModel):
    """Request to ensure a janua user exists for a sibling app's roster member."""

    email: EmailStr
    first_name: str = Field(min_length=1, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    # REQUIRED and never defaulted. Since migration 013 email is unique PER
    # TENANT, so `tenant_id` is what selects the identity pool. Defaulting it
    # (to None, or to any "current" tenant) would let a caller that forgot the
    # field create or mutate a user in the WRONG organization — a cross-tenant
    # identity bug that reads as success. The caller must state the pool.
    tenant_id: UUID
    # Mark the provisioned identity as a technical/service account rather than
    # a person. Defaults to False: a roster app that says nothing is
    # provisioning a colleague, which is the overwhelmingly common case and
    # today's only behaviour.
    #
    # Honoured ONLY on creation. An existing row is returned untouched by this
    # endpoint (see the handler docstring: this is provisioning, not
    # synchronization), and that rule holds for this field too — flipping a
    # live identity between "person" and "service" is an operator decision with
    # roster- and signature-visible consequences, not something a roster app
    # should be able to do as a side effect of a retry.
    is_service_account: bool = False


class ProvisionUserResponse(BaseModel):
    """Result of a provisioning call. `created` distinguishes 201 from 200."""

    id: str
    email: str
    status: str
    created: bool
    created_at: datetime
    # Echoes the identity's stored flag — for a pre-existing row this is the
    # STORED value, which may differ from what the caller requested, so a
    # caller can detect the "already exists, and it is/is not a service
    # account" case without a second read.
    is_service_account: bool = False


class UserLifecycleRequest(BaseModel):
    """Request to suspend or reactivate a roster member's janua access."""

    email: EmailStr
    # Required for the same reason as on ProvisionUserRequest: it selects the
    # per-tenant email pool. Guessing would suspend another org's user.
    tenant_id: UUID


class UserLifecycleResponse(BaseModel):
    """Result of a lifecycle call. `changed` is False when already in state."""

    id: str
    email: str
    status: str
    changed: bool
