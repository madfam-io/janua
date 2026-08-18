"""Canonical data-export serialization for GDPR/portability requests.

This module is the single source of truth for turning Janua's identity data
into a portable, machine-readable artifact for two consumers:

1. Per-user GDPR export (Articles 15 / 20) via the compliance data-subject
   request flow (:mod:`app.services.compliance_service` and
   :mod:`app.compliance.privacy.data_subject_handler`).
2. Admin bulk/tenant export via :mod:`app.services.migration_service`.

Security contract (non-negotiable)
----------------------------------
Janua is an identity provider. An export is portability *without* leaking
credentials. Every serializer here works from an explicit **allowlist** of
fields per model: a column is exported only if it is named in the allowlist.
Nothing is copied by iterating ``__table__.columns`` and hoping a denylist
catches the secrets. On top of the allowlist we keep a defensive
:data:`SECRET_FIELD_NAMES` denylist and a :func:`assert_no_secrets` auditor
that callers (and tests) can use to prove an artifact is clean.

Secret material that MUST NEVER appear in an export:

* ``password_hash`` (user credential)
* ``mfa_secret`` / TOTP seeds and ``mfa_backup_codes``
* session ``token`` / ``refresh_token`` and their JTIs
* OAuth ``access_token`` / ``refresh_token`` (provider credentials)
* OAuth client ``client_secret_hash`` / ``secret_hash`` and prefixes
* passkey ``public_key`` (credential material) — only metadata is exported
* webhook ``secret`` and email/reset/verification ``token`` values

For MFA, passkeys and OAuth we export *metadata* ("MFA is enabled",
"a passkey named 'MacBook' exists", "linked to GitHub") so the export is
useful for portability without handing over anything that authenticates.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence
# nosec B406 — we import ONLY saxutils.escape, and use it solely to ENCODE our
# own export values into XML output (see _to_xml); we never parse untrusted XML,
# which is what B406/defusedxml guards against. Escaping on output is the correct,
# injection-safe use of this helper.
from xml.sax.saxutils import escape as _xml_escape  # nosec B406

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    OAuthAccount,
    Organization,
    OrganizationMember,
    Passkey,
    Session,
    User,
    UserConsent,
)

# ---------------------------------------------------------------------------
# Secret denylist (defensive second layer; the allowlists below are primary)
# ---------------------------------------------------------------------------

#: Field / attribute names that must never be serialized into an export.
#: Matching is case-insensitive and substring-based via :func:`_is_secret_key`
#: so ``password_hash`` and ``hashed_password`` are both caught.
SECRET_FIELD_NAMES: frozenset = frozenset(
    {
        "password",
        "password_hash",
        "hashed_password",
        "mfa_secret",
        "totp_secret",
        "mfa_backup_codes",
        "backup_codes",
        "recovery_codes",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "access_token_jti",
        "refresh_token_jti",
        "session_token",
        "client_secret",
        "client_secret_hash",
        "client_secret_prefix",
        "secret",
        "secret_hash",
        "secret_prefix",
        "public_key",
        "private_key",
        "signing_key",
        "api_key",
        "encryption_key",
    }
)

#: Substrings that flag a field name as secret regardless of the exact column
#: name (covers future columns like ``webhook_secret`` or ``totp_seed``).
_SECRET_SUBSTRINGS: Sequence[str] = (
    "password",
    "secret",
    "private_key",
    "backup_code",
    "recovery_code",
    "totp",
    "mfa_secret",
    "seed",
)

#: Field names that are legitimately safe even though they contain a secret
#: substring (e.g. a boolean flag or a non-sensitive identifier).
_SECRET_ALLOWLIST_OVERRIDES: frozenset = frozenset(
    {
        "mfa_enabled",  # boolean flag, not the seed
    }
)


def _is_secret_key(key: str) -> bool:
    """Return True if a field name looks like secret/credential material."""
    lowered = key.lower()
    if lowered in _SECRET_ALLOWLIST_OVERRIDES:
        return False
    if lowered in SECRET_FIELD_NAMES:
        return True
    return any(sub in lowered for sub in _SECRET_SUBSTRINGS)


# ---------------------------------------------------------------------------
# Per-model allowlists (primary defense: only these columns are ever emitted)
# ---------------------------------------------------------------------------

#: Non-sensitive User columns safe to export. Deliberately excludes
#: password_hash, mfa_secret, mfa_backup_codes.
USER_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "email",
    "email_verified",
    "email_verified_at",
    "status",
    "first_name",
    "last_name",
    "username",
    "phone",
    "phone_number",
    "phone_verified",
    "avatar_url",
    "profile_image_url",
    "display_name",
    "bio",
    "timezone",
    "locale",
    "spanish_formality",
    "user_metadata",
    "tenant_id",
    "is_active",
    "is_admin",
    "mfa_enabled",  # flag only
    "last_login",
    "last_sign_in_at",
    "created_at",
    "updated_at",
)

ORGANIZATION_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "name",
    "slug",
    "subscription_tier",
    "product_tiers",
    "billing_plan",
    "billing_email",
    "description",
    "logo_url",
    "created_at",
    "updated_at",
)

MEMBERSHIP_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "organization_id",
    "role",
    "status",
    "joined_at",
    "created_at",
    "updated_at",
)

#: Session metadata only — NEVER token / refresh_token / *_jti.
SESSION_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "ip_address",
    "user_agent",
    "device_name",
    "device_fingerprint",
    "is_active",
    "revoked",
    "revoked_at",
    "revoked_reason",
    "is_trusted_device",
    "expires_at",
    "last_activity",
    "created_at",
)

#: OAuth linkage metadata only — NEVER access_token / refresh_token.
OAUTH_ACCOUNT_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "provider",
    "provider_user_id",
    "provider_email",
    "token_expires_at",
    "created_at",
    "updated_at",
)

#: OAuth grant/consent records (scopes the user approved for a client).
OAUTH_GRANT_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "client_id",
    "scopes",
    "granted_at",
    "expires_at",
    "revoked_at",
    "created_at",
    "updated_at",
)

#: Passkey metadata only — NEVER public_key / credential material export.
PASSKEY_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "name",
    "authenticator_attachment",
    "sign_count",
    "created_at",
    "last_used_at",
)

AUDIT_LOG_EXPORT_FIELDS: Sequence[str] = (
    "id",
    "action",
    "resource_type",
    "resource_id",
    "details",
    "ip_address",
    "user_agent",
    "created_at",
)


# ---------------------------------------------------------------------------
# JSON-safe value coercion
# ---------------------------------------------------------------------------


def _coerce(value: Any) -> Any:
    """Coerce a SQLAlchemy column value into a JSON-serializable form."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_coerce(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in value.items()}
    # Fallback: stringify unknown types rather than risk leaking a repr with
    # embedded credentials from an unexpected object.
    return str(value)


def _row_to_dict(instance: Any, fields: Sequence[str]) -> Dict[str, Any]:
    """Project an ORM instance onto an allowlist of fields, secret-checked.

    Even though ``fields`` is a curated allowlist, we re-assert that no field
    name is secret. This makes it impossible to widen an allowlist to include
    a credential column without :func:`assert_no_secrets` failing loudly.
    """
    out: Dict[str, Any] = {}
    for field in fields:
        if _is_secret_key(field):
            # Defensive: a curated list should never contain a secret field.
            raise ValueError(
                f"Refusing to export secret-like field '{field}' from " f"{type(instance).__name__}"
            )
        out[field] = _coerce(getattr(instance, field, None))
    return out


# ---------------------------------------------------------------------------
# Collection: gather a single user's exportable data
# ---------------------------------------------------------------------------


async def collect_user_export_data(
    session: AsyncSession,
    user_id: str,
    *,
    include_audit_logs: bool = True,
    date_range_start: Optional[datetime] = None,
    date_range_end: Optional[datetime] = None,
    portable_only: bool = False,
) -> Dict[str, Any]:
    """Gather all exportable data for ``user_id`` from the real models.

    Parameters
    ----------
    session:
        Active async DB session.
    user_id:
        Subject user id (str or UUID-compatible string).
    include_audit_logs:
        Include the user's audit-log entries (Article 15). Skipped for the
        strict Article 20 portability subset when ``portable_only`` is set.
    date_range_start / date_range_end:
        Optional filter applied to audit-log ``created_at``.
    portable_only:
        When True, restrict the export to data the user actively provided
        (profile, org memberships, OAuth grants) per GDPR Article 20's
        narrower "data provided by the data subject" scope, and omit
        server-generated telemetry like sessions and audit logs.

    Returns
    -------
    dict
        A JSON-serializable structure. Contains no secret material.
    """
    uid = uuid.UUID(str(user_id))

    user = (await session.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if user is None:
        raise ValueError(f"User not found: {user_id}")

    export: Dict[str, Any] = {
        "export_metadata": {
            "schema_version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "subject_user_id": str(uid),
            "article": "GDPR Article 20" if portable_only else "GDPR Article 15",
            "portable_only": portable_only,
            "excludes": [
                "password hashes",
                "MFA secrets and backup codes",
                "session and OAuth tokens",
                "passkey / client credential material",
            ],
        },
        "user": _row_to_dict(user, USER_EXPORT_FIELDS),
    }

    # --- Organization memberships (+ light org profile) ---------------------
    memberships = (
        (await session.execute(select(OrganizationMember).where(OrganizationMember.user_id == uid)))
        .scalars()
        .all()
    )
    membership_records: List[Dict[str, Any]] = []
    org_ids = {m.organization_id for m in memberships if m.organization_id is not None}
    orgs_by_id: Dict[Any, Organization] = {}
    if org_ids:
        orgs = (
            (await session.execute(select(Organization).where(Organization.id.in_(org_ids))))
            .scalars()
            .all()
        )
        orgs_by_id = {o.id: o for o in orgs}
    for member in memberships:
        record = _row_to_dict(member, MEMBERSHIP_EXPORT_FIELDS)
        org = orgs_by_id.get(member.organization_id)
        record["organization"] = (
            _row_to_dict(org, ORGANIZATION_EXPORT_FIELDS) if org is not None else None
        )
        membership_records.append(record)
    export["organization_memberships"] = membership_records

    # --- OAuth grants (client consents) ------------------------------------
    grants = (
        (await session.execute(select(UserConsent).where(UserConsent.user_id == uid)))
        .scalars()
        .all()
    )
    export["oauth_grants"] = [_row_to_dict(g, OAUTH_GRANT_EXPORT_FIELDS) for g in grants]

    # --- Linked OAuth / social accounts (metadata only) --------------------
    oauth_accounts = (
        (await session.execute(select(OAuthAccount).where(OAuthAccount.user_id == uid)))
        .scalars()
        .all()
    )
    export["linked_accounts"] = [
        _row_to_dict(a, OAUTH_ACCOUNT_EXPORT_FIELDS) for a in oauth_accounts
    ]

    # --- MFA / passkey enrollment (metadata only, no secrets) --------------
    passkeys = (
        (await session.execute(select(Passkey).where(Passkey.user_id == uid))).scalars().all()
    )
    export["security"] = {
        "mfa_enabled": bool(user.mfa_enabled),
        "mfa_methods": (["totp"] if user.mfa_enabled else []),
        "passkeys": [_row_to_dict(p, PASSKEY_EXPORT_FIELDS) for p in passkeys],
        "note": (
            "TOTP seeds, MFA backup codes and passkey public keys are "
            "intentionally excluded as credential material."
        ),
    }

    if portable_only:
        # Article 20 subset: omit server-generated telemetry.
        return export

    # --- Sessions (metadata only, no tokens) -------------------------------
    sessions = (
        (await session.execute(select(Session).where(Session.user_id == uid))).scalars().all()
    )
    export["sessions"] = [_row_to_dict(s, SESSION_EXPORT_FIELDS) for s in sessions]

    # --- Audit-log entries for this user -----------------------------------
    if include_audit_logs:
        audit_stmt = select(AuditLog).where(AuditLog.user_id == uid)
        if date_range_start is not None:
            audit_stmt = audit_stmt.where(AuditLog.created_at >= date_range_start)
        if date_range_end is not None:
            audit_stmt = audit_stmt.where(AuditLog.created_at <= date_range_end)
        audit_stmt = audit_stmt.order_by(AuditLog.created_at.desc())
        audit_entries = (await session.execute(audit_stmt)).scalars().all()
        export["audit_logs"] = [_row_to_dict(a, AUDIT_LOG_EXPORT_FIELDS) for a in audit_entries]

    return export


# ---------------------------------------------------------------------------
# Collection: gather a tenant/organization's users (admin bulk export)
# ---------------------------------------------------------------------------


async def collect_organization_users(
    session: AsyncSession,
    organization_id: Optional[str],
    *,
    export_type: str = "user_data",
    include_audit_logs: bool = False,
) -> Dict[str, Any]:
    """Gather users (and optionally audit logs) for an admin bulk export.

    Parameters
    ----------
    organization_id:
        Restrict to members of this organization. When ``None``, export all
        users (whole-tenant / instance export).
    export_type:
        One of ``user_data`` (default), ``organization_data`` (users grouped
        under their org profile), or ``audit_logs`` (audit entries only).
    include_audit_logs:
        Force-include audit logs regardless of ``export_type``.
    """
    org_uuid = uuid.UUID(str(organization_id)) if organization_id else None

    # Resolve the user set (scoped to an org when requested).
    if org_uuid is not None:
        member_rows = (
            (
                await session.execute(
                    select(OrganizationMember.user_id).where(
                        OrganizationMember.organization_id == org_uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        member_ids = list({uid for uid in member_rows if uid is not None})
        users = (
            (await session.execute(select(User).where(User.id.in_(member_ids)))).scalars().all()
            if member_ids
            else []
        )
    else:
        users = (await session.execute(select(User))).scalars().all()

    result: Dict[str, Any] = {
        "export_metadata": {
            "schema_version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "export_type": export_type,
            "organization_id": str(org_uuid) if org_uuid else None,
            "record_count": len(users),
            "excludes": [
                "password hashes",
                "MFA secrets and backup codes",
                "session and OAuth tokens",
                "passkey / client credential material",
            ],
        }
    }

    if export_type == "audit_logs" or include_audit_logs:
        user_ids = [u.id for u in users]
        audit_stmt = select(AuditLog)
        if org_uuid is not None:
            # Scope audit logs to the resolved user set for an org export.
            audit_stmt = audit_stmt.where(AuditLog.user_id.in_(user_ids or [uuid.uuid4()]))
        audit_stmt = audit_stmt.order_by(AuditLog.created_at.desc())
        audit_entries = (await session.execute(audit_stmt)).scalars().all()
        result["audit_logs"] = [_row_to_dict(a, AUDIT_LOG_EXPORT_FIELDS) for a in audit_entries]
        if export_type == "audit_logs":
            return result

    if export_type == "organization_data":
        # Group users under organization profiles.
        orgs_stmt = select(Organization)
        if org_uuid is not None:
            orgs_stmt = orgs_stmt.where(Organization.id == org_uuid)
        orgs = (await session.execute(orgs_stmt)).scalars().all()
        result["organizations"] = [_row_to_dict(o, ORGANIZATION_EXPORT_FIELDS) for o in orgs]

    result["users"] = [_row_to_dict(u, USER_EXPORT_FIELDS) for u in users]
    return result


# ---------------------------------------------------------------------------
# Serialization to bytes (json / csv / xml) and downloadable artifacts
# ---------------------------------------------------------------------------


def _flatten_users_for_tabular(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract the user rows from a bulk/user export for CSV/XML output."""
    if "users" in data and isinstance(data["users"], list):
        return data["users"]
    if "user" in data and isinstance(data["user"], dict):
        return [data["user"]]
    return []


def serialize_export(data: Dict[str, Any], export_format: str = "json") -> bytes:
    """Serialize a collected export dict to bytes in the requested format.

    JSON is the canonical, lossless format. CSV and XML flatten the user
    records (the portable core) for interoperability with spreadsheet /
    legacy tooling; nested structures are JSON-encoded within cells so no
    data is silently dropped.
    """
    fmt = (export_format or "json").lower()

    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False).encode("utf-8")

    if fmt == "csv":
        rows = _flatten_users_for_tabular(data)
        buffer = io.StringIO()
        if rows:
            # Union of keys preserves first-seen order for stable columns.
            fieldnames: List[str] = []
            for row in rows:
                for key in row:
                    if key not in fieldnames:
                        fieldnames.append(key)
            writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        key: (
                            json.dumps(value, ensure_ascii=False)
                            if isinstance(value, (dict, list))
                            else value
                        )
                        for key, value in row.items()
                    }
                )
        return buffer.getvalue().encode("utf-8")

    if fmt == "xml":
        return _to_xml(data).encode("utf-8")

    raise ValueError(f"Unsupported export format: {export_format}")


def _to_xml(data: Any, root_tag: str = "export") -> str:
    """Render a nested dict/list into a minimal, well-formed XML document."""

    def render(value: Any, tag: str) -> str:
        safe_tag = _xml_tag(tag)
        if isinstance(value, dict):
            inner = "".join(render(v, k) for k, v in value.items())
            return f"<{safe_tag}>{inner}</{safe_tag}>"
        if isinstance(value, (list, tuple)):
            inner = "".join(render(item, "item") for item in value)
            return f"<{safe_tag}>{inner}</{safe_tag}>"
        if value is None:
            return f"<{safe_tag}/>"
        return f"<{safe_tag}>{_xml_escape(str(value))}</{safe_tag}>"

    body = render(data, root_tag)
    return f'<?xml version="1.0" encoding="UTF-8"?>{body}'


def _xml_tag(tag: str) -> str:
    """Sanitize a dict key into a valid XML tag name."""
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in str(tag))
    if not cleaned or not (cleaned[0].isalpha() or cleaned[0] == "_"):
        cleaned = f"_{cleaned}"
    return cleaned


def build_export_archive(
    data: Dict[str, Any],
    *,
    manifest_name: str = "export.json",
    section_files: bool = True,
) -> bytes:
    """Build a zip archive containing the export as JSON files.

    The archive always contains ``manifest_name`` with the full export. When
    ``section_files`` is set, each top-level section is also written as its
    own JSON file for easier consumption (e.g. ``audit_logs.json``).
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            manifest_name,
            json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"),
        )
        if section_files:
            for key, value in data.items():
                if key == "export_metadata":
                    continue
                archive.writestr(
                    f"{key}.json",
                    json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8"),
                )
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Secret auditor — usable by callers and tests to prove an artifact is clean
# ---------------------------------------------------------------------------


def find_secret_fields(data: Any, _path: str = "") -> List[str]:
    """Recursively find any secret-like *keys* in a nested structure.

    Returns a list of dotted paths for offending keys. An empty list means the
    structure carries no fields whose name indicates credential material.
    """
    found: List[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            here = f"{_path}.{key}" if _path else str(key)
            if _is_secret_key(str(key)):
                found.append(here)
            found.extend(find_secret_fields(value, here))
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            found.extend(find_secret_fields(item, f"{_path}[{index}]"))
    return found


def assert_no_secrets(data: Any) -> None:
    """Raise ``ValueError`` if ``data`` contains any secret-like field names."""
    offenders = find_secret_fields(data)
    if offenders:
        raise ValueError(
            "Export contains secret-like fields that must not be serialized: "
            + ", ".join(sorted(offenders))
        )


def contains_secret_values(data: Any, secrets: Iterable[str]) -> Optional[str]:
    """Return the first sentinel secret value found anywhere in ``data``.

    Used primarily by tests: seed models with known sentinel secret strings,
    serialize, and assert none of the sentinels survive into the artifact.
    ``None`` means no sentinel leaked.
    """
    needles = [s for s in secrets if s]

    def walk(value: Any) -> Optional[str]:
        if isinstance(value, str):
            for needle in needles:
                if needle in value:
                    return needle
            return None
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str):
                    for needle in needles:
                        if needle in key:
                            return needle
                hit = walk(item)
                if hit:
                    return hit
            return None
        if isinstance(value, (list, tuple)):
            for item in value:
                hit = walk(item)
                if hit:
                    return hit
        return None

    return walk(data)
