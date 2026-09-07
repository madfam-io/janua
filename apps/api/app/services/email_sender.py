"""Per-tenant SENDER identity for transactional email — Phase 2.

This is the other half of `email_branding.py`. That module resolves what the
BODY of a message looks like; this one resolves the From line itself. Read
`docs/EMAIL_SENDER_POLICY.md` first: Phase 1 kept ONE sender —
`MADFAM <hola@madfam.io>` — for every message from every platform, because the
client was meeting our ecosystem for the first time and we did not control
their sending domain. Phase 2 begins per-client, the day we do.

    Phase 1   From: MADFAM <hola@madfam.io>       (every tenant)
    Phase 2   From: Crea Tu Mundo <hola@creatumundo.mx>   (CTM hosts)

WHY NOW. Owner directive, 2026-09-06: `creatumundo.mx` is CTM's own domain,
MADFAM manages it, and mail to CTM families should come from CTM. The policy
always said this was gated on exactly one thing — that domain being verified in
Resend — and the domain becoming ours is what unblocks the verification.

THE GATE IS THE WHOLE POINT OF THIS MODULE. Resend does not degrade when you
send from a domain it has not verified: it REJECTS the call. An unverified
sender is not a message in the spam folder, it is no message at all, and the
message in question is a sign-in link. So the sender table below is not
consulted on its own — every candidate address is checked against
`settings.resend_verified_domains_list` (env `RESEND_VERIFIED_DOMAINS`,
default `madfam.io`) and an address on an unverified domain is DOWNGRADED, not
sent. See `_fallback_for`.

The downgrade is deliberately partial: the tenant's DISPLAY NAME survives, only
the address reverts.

    creatumundo.mx NOT yet verified -> Crea Tu Mundo <hola@madfam.io>
    creatumundo.mx verified         -> Crea Tu Mundo <hola@creatumundo.mx>

That means merging this branch changes nothing about deliverability, and the
production cutover is a one-line manifest edit (add `creatumundo.mx` to
`RESEND_VERIFIED_DOMAINS`) with a one-line rollback (remove it). The code path
that runs before and after verification is the same code path, so the cutover
is not also a first execution.

WHY THE SIGNAL IS THE REDIRECT HOST. Same reason as `email_branding.py`: the
auth mailer runs inside FastAPI BackgroundTasks with no DB session, so the
per-org white-label table is unreachable at send time. The magic-link
`redirect_url` host names the product the recipient is being sent back to, and
it is the signal `resolve_sender` was built to read — see the "seam that makes
Phase 2 cheap" section of the policy doc. This module is that seam, filled in.

WHY THE HOST TABLE IS NOT SHARED WITH `email_branding.CTM_HOSTS`. It IS shared:
`SENDER_HOSTS` below is built from the branding registry's host tuple so a host
can never be CTM-branded in the body and MADFAM on the envelope (or vice
versa). One tenant, one host list.

2026-09-07 — THE TABLE MOVED, THE BEHAVIOUR DID NOT. The per-tenant sender is
now a `SenderBinding` record in `sender_binding.py` (display name, address,
reply-to, PROVIDER, ACCOUNT, credential reference, per-account verified
domains) rather than the bare triple that used to live in `_TENANT_SENDERS`
here. Two owner requirements drove that, and neither fits a triple:

  * a branded From is now restricted to vCTO clients — the gate is
    `sender_policy.is_vcto_entitled`, consulted below;
  * a client must be able to move to their OWN provider account — that is the
    binding's `account` / `credential_ref` pair, read at send time by
    `sender_credentials`.

`_TENANT_SENDERS` and `SENDER_HOSTS` are kept as DERIVED views over the binding
registry: they were public names with tests pinning them, and deriving rather
than deleting means the registry stays the single source while nothing that
imported them breaks. Resolution order and the verified-domain downgrade are
unchanged; a tenant that passes the gate resolves exactly as it did before.
"""

from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from app.config import settings
from app.services.sender_binding import (
    SenderBinding,
    all_bindings,
    resolve_binding,
)
from app.services.sender_binding import tenant_for_host as _binding_tenant_for_host
from app.services.sender_binding import tenant_for_org_id as _binding_tenant_for_org_id
from app.services.sender_policy import is_vcto_entitled

# --------------------------------------------------------------------------
# A sender is a (display name, address, reply-to) triple. Reply-to is carried
# explicitly rather than defaulted to the From address because the two diverge
# the moment a tenant's mailbox is hosted somewhere the sending domain is not
# — which is exactly CTM's shape: Resend sends `hola@creatumundo.mx`, Proton
# RECEIVES it. Keeping the field means the reply destination is a decision the
# table records rather than an accident of the sending config.
# --------------------------------------------------------------------------
Sender = Tuple[str, str, str]

# The MADFAM default. Reads from settings so an operator can still move the
# platform sender with env alone, exactly as before this module existed.
DEFAULT_SENDER_NAME = "MADFAM"
DEFAULT_SENDER_ADDRESS = "hola@madfam.io"


def _as_triple(binding: SenderBinding) -> Sender:
    """The (name, address, reply-to) view of a binding."""
    return (binding.display_name, binding.from_address, binding.reply_to)


# Crea Tu Mundo. `hola@creatumundo.mx` per the owner directive (2026-09-06);
# replies land in the Proton mailbox for that domain, which is why reply-to is
# the same address rather than bouncing a family back to hola@madfam.io.
# DERIVED from the binding registry — the values are identical to the literal
# that used to sit here, but there is now one place that decides them.
CTM_SENDER: Sender = _as_triple(resolve_binding("ctm"))

#: Every tenant's sender triple. A DERIVED view over `sender_binding._BINDINGS`
#: (see the module docstring): kept because it was a public name with tests
#: pinning it, rebuilt from the registry so the two cannot drift.
_TENANT_SENDERS: Dict[str, Sender] = {
    tenant: _as_triple(binding) for tenant, binding in all_bindings().items()
}

# Deliberately the SAME hosts the body branding uses. A host that renders the
# Crea Tu Mundo header must also carry the Crea Tu Mundo envelope; deriving the
# tuple rather than restating it makes the two impossible to drift apart. The
# binding carries `hosts=CTM_HOSTS` by reference, so this is still that exact
# tuple object and `SENDER_HOSTS["ctm"] is CTM_HOSTS` still holds.
SENDER_HOSTS: Dict[str, Tuple[str, ...]] = {
    tenant: binding.hosts for tenant, binding in all_bindings().items()
}


def _default_sender() -> Sender:
    """`MADFAM <hola@madfam.io>`, or whatever env overrides it to."""
    name = settings.FROM_NAME or settings.EMAIL_FROM_NAME or DEFAULT_SENDER_NAME
    address = settings.FROM_EMAIL or settings.EMAIL_FROM_ADDRESS or DEFAULT_SENDER_ADDRESS
    return name, address, address


def domain_of(address: Optional[str]) -> str:
    """The lowercased domain part of an address, or "" if there isn't one."""
    if not address or "@" not in address:
        return ""
    return address.rsplit("@", 1)[1].strip().lower()


def is_verified_domain(address: Optional[str], binding: Optional[SenderBinding] = None) -> bool:
    """True when `address`'s domain is verified FOR THE ACCOUNT THAT WILL SEND.

    Exact domain match, NOT a suffix match: a verified `madfam.io` must not
    silently authorise `evil.madfam.io`, and Resend verifies each sending
    domain separately anyway.

    WHY THE ACCOUNT MATTERS. Domain verification in Resend is a property of an
    ACCOUNT, not of a domain. `creatumundo.mx` verified on MADFAM's account
    says nothing about whether it is verified on CTM's own account, so once a
    binding moves to `account="tenant"` the global `RESEND_VERIFIED_DOMAINS`
    (which describes MADFAM's account) is the wrong authority and the binding's
    own `verified_domains` is the right one. A binding on MADFAM's account, or
    no binding at all, reads the global list exactly as before.
    """
    domain = domain_of(address)
    if not domain:
        return False
    if binding is not None and binding.verified_domains:
        return domain in {d.strip().lower() for d in binding.verified_domains}
    return domain in settings.resend_verified_domains_list


def _tenant_for_host(host: Optional[str]) -> Optional[str]:
    """Map a redirect host to a sender tenant key, or None for the default.

    Delegates to the binding registry so host->tenant is decided in exactly one
    place. Same dot-boundary matching as before.
    """
    return _binding_tenant_for_host(host)


def _tenant_for_org_id(org_id: Optional[object]) -> Optional[str]:
    """Map an organization id to a sender tenant key, or None.

    Delegates to the binding registry, which carries each tenant's `org_id`.
    `CTM_ORG_ID` is still the value behind CTM's entry.
    """
    return _binding_tenant_for_org_id(org_id)


def _fallback_for(sender: Sender) -> Sender:
    """Downgrade a sender whose domain Resend has not verified.

    Keeps the tenant's DISPLAY NAME and reverts only the address, so a CTM
    recipient still sees "Crea Tu Mundo" in their inbox list before the domain
    is verified — the brand arrives early, the deliverability risk never does.
    Reply-to follows the address it can actually be sent from.
    """
    name, _address, _reply_to = sender
    _dname, default_address, default_reply = _default_sender()
    if not is_verified_domain(default_address):
        # The platform's OWN address is unverified. That is a misconfiguration
        # of RESEND_VERIFIED_DOMAINS, not a tenant problem — return it anyway
        # rather than inventing a third address, so the operator sees the real
        # rejection from Resend instead of mail silently coming from elsewhere.
        return name, default_address, default_reply
    return name, default_address, default_reply


def tenant_for(
    host: Optional[str] = None,
    redirect_url: Optional[str] = None,
    org_id: Optional[object] = None,
) -> Optional[str]:
    """The tenant key for one message, or None for the platform default.

    Factored out of `sender_for` because the binding, the vCTO gate and the
    credential all need the same answer, and three walks of the same precedence
    would be three chances for them to disagree about who is sending.
    """
    tenant = _tenant_for_org_id(org_id)
    if tenant is None and host:
        tenant = _tenant_for_host(host)
    if tenant is None and redirect_url:
        tenant = _tenant_for_host(urlparse(redirect_url).hostname)
    return tenant


def binding_for(
    host: Optional[str] = None,
    redirect_url: Optional[str] = None,
    org_id: Optional[object] = None,
) -> SenderBinding:
    """The `SenderBinding` one message resolves to.

    The account/provider/credential view of the same resolution `sender_for`
    performs. The send path needs this to know WHICH ACCOUNT to send on; see
    `sender_credentials.resolve_credential`.

    NOTE this returns the binding the tenant WOULD use, without applying the
    vCTO gate — a gated-off tenant sends on the platform account by definition,
    and `resend_email_service` reads the gate through `sender_for` before it
    ever asks for a credential.
    """
    return resolve_binding(tenant_for(host=host, redirect_url=redirect_url, org_id=org_id))


def sender_for(
    host: Optional[str] = None,
    redirect_url: Optional[str] = None,
    org_id: Optional[object] = None,
    vcto_entitled: Optional[bool] = None,
) -> Sender:
    """The (display name, from address, reply-to) for one message.

    Resolution order, highest precedence first:

      1. `org_id` — a caller that already knows the tenant is authoritative.
      2. `host` — a bare hostname, when a caller has one directly.
      3. `redirect_url` — the magic-link redirect, whose host names the
         product; this is what the auth mailer actually has at send time.
      4. Nothing recognised -> the MADFAM default.

    TWO gates then apply to the resolved tenant, in this order:

      * **The vCTO gate** (`sender_policy.is_vcto_entitled`). A branded From
        line is reserved for clients whose infrastructure MADFAM operates —
        owner directive 2026-09-06. A tenant that does not pass keeps its
        DISPLAY NAME and reverts to the platform address, which is the same
        partial downgrade the verification gate performs, for the same reason:
        the brand is cosmetic, the address is operational. `vcto_entitled`
        lets a caller holding a DB session supply the authoritative answer;
        without one the policy module's cache decides and fails closed.

      * **The verified-domain gate**, now evaluated against the ACCOUNT the
        binding names (see `is_verified_domain`). An unverified domain is
        downgraded to the default address, keeping the tenant display name.

    Neither gate is bypassable from a caller: passing `vcto_entitled=True` for
    a tenant whose domain is unverified still downgrades, because the second
    gate is about whether Resend will accept the send at all.
    """
    tenant = tenant_for(host=host, redirect_url=redirect_url, org_id=org_id)

    if tenant is None:
        return _default_sender()

    binding = resolve_binding(tenant)
    sender = _as_triple(binding)

    if not is_vcto_entitled(tenant, vcto_entitled=vcto_entitled):
        # Not a vCTO client: the name ships, the domain does not.
        return _fallback_for(sender)

    if not is_verified_domain(sender[1], binding=binding):
        return _fallback_for(sender)
    return sender


def sender_for_address(
    from_email: Optional[str],
    from_name: Optional[str] = None,
    host: Optional[str] = None,
    redirect_url: Optional[str] = None,
    org_id: Optional[object] = None,
    vcto_entitled: Optional[bool] = None,
) -> Sender:
    """Honour a caller's explicit From, but only from a verified domain.

    The internal door (`POST /api/v1/email/send`) accepts `from_email` /
    `from_name` from other MADFAM services. Those fields were previously
    ignored outright, which was safe but opaque. Honouring them is only safe
    under the same gate everything else is under: an arbitrary caller-supplied
    domain is exactly the input that would hand Resend a rejection, or worse
    let one service send as another's brand.

    So: an explicit address is used when its domain is in
    `RESEND_VERIFIED_DOMAINS`, and otherwise the caller's From is DISCARDED and
    the host rule decides. A caller's display name is still honoured in the
    fallback — naming yourself is harmless, claiming a domain is not.

    THE vCTO GATE APPLIES HERE TOO, and it has to. If an explicit `from_email`
    could reach a tenant domain without passing the gate, then "restrict
    branded sending to vCTO clients" would hold for the auth mailer and be
    bypassable by any service holding the internal API key — which is the one
    caller most likely to be automating a client's mail. So an explicit address
    on a TENANT's domain is honoured only when that tenant passes the gate; an
    address on MADFAM's own verified domain is unaffected, because sending as
    MADFAM was never the branded privilege.
    """
    if from_email and is_verified_domain(from_email):
        claimed = _tenant_for_verified_address(from_email)
        if claimed is None or is_vcto_entitled(claimed, vcto_entitled=vcto_entitled):
            name = from_name or _default_sender()[0]
            return name, from_email.strip(), from_email.strip()

    name, address, reply_to = sender_for(
        host=host,
        redirect_url=redirect_url,
        org_id=org_id,
        vcto_entitled=vcto_entitled,
    )
    if from_name:
        name = from_name
    return name, address, reply_to


def _tenant_for_verified_address(address: Optional[str]) -> Optional[str]:
    """The tenant whose binding claims `address`'s domain, or None.

    Used to decide whether a caller-supplied From is asking to send as a
    CLIENT's brand (gated) or merely as MADFAM (never gated). Matches on the
    binding's own `from_address` domain, which is the domain the tenant was
    onboarded with.
    """
    domain = domain_of(address)
    if not domain:
        return None
    for tenant, binding in all_bindings().items():
        if domain_of(binding.from_address) == domain:
            return tenant
        if domain in {d.strip().lower() for d in binding.verified_domains}:
            return tenant
    return None
