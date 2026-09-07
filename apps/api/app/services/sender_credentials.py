"""Resolve a binding's provider credential. The ONLY module that reads one.

A `SenderBinding` carries a `credential_ref` — a NAME, never a value. This
module turns that name into the secret at send time, and it is deliberately the
single place in the transactional-mail stack that ever holds one. Everything
else (the binding registry, the policy gate, the switch script, the logs) works
with references, which is what makes a binding safe to print in a PR diff and
safe for an operator script to echo.

TWO REFERENCE SHAPES, ONE FUNCTION

    RESEND_API_KEY                                   -> environment variable
    secret/data/janua/senders/ctm#resend_api_key     -> Vault path # field

Both go through `app.core.secrets_provider`, which is already the repo's
abstraction for exactly this (SOC 2 CF-06): it returns a `VaultSecretsProvider`
when `VAULT_ADDR`/`VAULT_TOKEN` are set and an `EnvSecretsProvider` otherwise.
Reusing it means a tenant credential lands in Vault through the same path as
every other janua secret, with the same 300s cache, rather than through a
second mechanism invented here.

WHY THE `#field` SUFFIX. Vault KV v2 stores a MAP at a path. The existing
provider is constructed around one path (`VAULT_SECRET_PATH`, default
`secret/data/janua`) and reads keys out of it, which is right for janua's own
config but wrong for per-tenant secrets: each tenant's credential should live at
its own path so it can be scoped by its own Vault policy, and so that granting
an operator access to one tenant's key does not grant them janua's whole config
map. The `#field` suffix names the key within that per-tenant path.

NEVER LOGGED. No function here returns, formats, or logs a credential value.
Failures log the REFERENCE and the reason, which is enough to diagnose
("wrong path", "field missing") and never enough to leak. `has_credential`
exists so an operator script can answer "is it there?" without the value ever
crossing a process boundary.
"""

from __future__ import annotations

import os
from typing import Optional

import structlog

from app.config import settings
from app.services.sender_binding import (
    ACCOUNT_TENANT,
    MADFAM_RESEND_CREDENTIAL_REF,
    SenderBinding,
)

logger = structlog.get_logger()


class SenderCredentialError(RuntimeError):
    """A binding's credential could not be resolved.

    Raised rather than returning None so a misconfigured TENANT-account binding
    is loud. The send path catches it and falls back to the platform sender
    (see `resend_email_service`), because a sign-in link that does not arrive is
    worse than one from the platform address — but the exception is what makes
    the fallback an observable event instead of a silent one.
    """


def _is_vault_ref(credential_ref: str) -> bool:
    """True for a Vault path reference, False for an env var name.

    A Vault path contains a `/`; an environment variable name cannot. That is
    the whole discriminator, and it is unambiguous because POSIX env names are
    restricted to `[A-Za-z_][A-Za-z0-9_]*`.
    """
    return "/" in credential_ref


def _split_vault_ref(credential_ref: str) -> tuple[str, str]:
    """`secret/data/x/y#field` -> (`secret/data/x/y`, `field`).

    A reference with no `#` defaults to the field `api_key`, so the common case
    can be written as a bare path.
    """
    if "#" in credential_ref:
        path, field = credential_ref.rsplit("#", 1)
        return path.strip(), field.strip()
    return credential_ref.strip(), "api_key"


async def resolve_credential(binding: SenderBinding) -> Optional[str]:
    """The provider credential for `binding`, or None to use process defaults.

    Returns None for a binding on MADFAM's own account whose reference is the
    platform key: the Resend SDK is already configured with
    `settings.RESEND_API_KEY` at service construction, so returning None means
    "change nothing", which keeps the pre-existing path byte-identical.

    Raises `SenderCredentialError` when a TENANT-account binding's credential
    is missing — that binding cannot send at all, and pretending otherwise
    would hand Resend someone else's key.
    """
    ref = (binding.credential_ref or "").strip()

    # MADFAM account on the platform key: nothing to resolve.
    if not binding.is_on_tenant_account and ref == MADFAM_RESEND_CREDENTIAL_REF:
        return None

    value = await _read_reference(ref)

    if value:
        return value

    if binding.account == ACCOUNT_TENANT:
        logger.error(
            "sender_credentials.missing_tenant_credential",
            tenant=binding.tenant,
            credential_ref=ref,  # a NAME, never a value
            provider=binding.provider,
        )
        raise SenderCredentialError(
            f"credential {ref!r} for tenant {binding.tenant!r} is not set; "
            "the binding is on the tenant's own account and cannot send without it"
        )

    logger.warning(
        "sender_credentials.missing_credential_using_platform_default",
        tenant=binding.tenant,
        credential_ref=ref,
    )
    return None


async def _read_reference(ref: str) -> Optional[str]:
    """Read one credential reference. Never logs the value."""
    if not ref:
        return None

    if not _is_vault_ref(ref):
        # An env var name. `settings` first so a value supplied through the
        # app's own config surface wins, then the raw environment.
        from_settings = getattr(settings, ref, None)
        if isinstance(from_settings, str) and from_settings.strip():
            return from_settings.strip()
        raw = os.environ.get(ref, "").strip()
        return raw or None

    path, field = _split_vault_ref(ref)
    try:
        # Imported lazily: the module-level singleton in secrets_provider is
        # built on first use, and importing it at module scope would build it
        # during test collection where VAULT_ADDR is deliberately unset.
        import hvac  # noqa: F401  (presence check; the provider imports it too)
    except ImportError:
        logger.warning("sender_credentials.hvac_unavailable", credential_ref=ref)
        return None

    vault_addr = os.environ.get("VAULT_ADDR", "").strip()
    vault_token = os.environ.get("VAULT_TOKEN", "").strip()
    if not (vault_addr and vault_token):
        logger.warning("sender_credentials.vault_not_configured", credential_ref=ref)
        return None

    try:
        from app.core.secrets_provider import VaultSecretsProvider

        provider = VaultSecretsProvider(
            vault_addr=vault_addr,
            vault_token=vault_token,
            secret_path=path,
        )
        value = await provider.get_secret(field)
    except Exception as exc:  # pragma: no cover - exercised via the error path
        # `str(exc)` from hvac names the path and the HTTP status, never the
        # secret; the value never enters an exception in the first place.
        logger.warning(
            "sender_credentials.vault_read_failed",
            credential_ref=ref,
            error=str(exc),
        )
        return None

    return value.strip() if isinstance(value, str) and value.strip() else None


async def has_credential(binding: SenderBinding) -> bool:
    """True when this binding's credential resolves to something.

    For operator tooling: answers "is the key in place?" without the value
    crossing a process boundary or entering a log line.
    """
    try:
        if not binding.is_on_tenant_account:
            ref = (binding.credential_ref or "").strip()
            if ref == MADFAM_RESEND_CREDENTIAL_REF:
                return bool((settings.RESEND_API_KEY or "").strip())
        return await resolve_credential(binding) is not None
    except SenderCredentialError:
        return False
