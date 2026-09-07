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
"""

from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from app.config import settings
from app.services.email_branding import CTM_HOSTS, CTM_ORG_ID, _host_matches

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

# Crea Tu Mundo. `hola@creatumundo.mx` per the owner directive (2026-09-06);
# replies land in the Proton mailbox for that domain, which is why reply-to is
# the same address rather than bouncing a family back to hola@madfam.io.
CTM_SENDER: Sender = (
    "Crea Tu Mundo",
    "hola@creatumundo.mx",
    "hola@creatumundo.mx",
)

_TENANT_SENDERS: Dict[str, Sender] = {
    "ctm": CTM_SENDER,
}

# Deliberately the SAME hosts the body branding uses. A host that renders the
# Crea Tu Mundo header must also carry the Crea Tu Mundo envelope; deriving the
# tuple rather than restating it makes the two impossible to drift apart.
SENDER_HOSTS: Dict[str, Tuple[str, ...]] = {
    "ctm": CTM_HOSTS,
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


def is_verified_domain(address: Optional[str]) -> bool:
    """True when `address`'s domain is listed as Resend-verified.

    Exact domain match, NOT a suffix match: a verified `madfam.io` must not
    silently authorise `evil.madfam.io`, and Resend verifies each sending
    domain separately anyway.
    """
    domain = domain_of(address)
    if not domain:
        return False
    return domain in settings.resend_verified_domains_list


def _tenant_for_host(host: Optional[str]) -> Optional[str]:
    """Map a redirect host to a sender tenant key, or None for the default."""
    if not host:
        return None
    for tenant, patterns in SENDER_HOSTS.items():
        for pattern in patterns:
            if _host_matches(host, pattern):
                return tenant
    return None


def _tenant_for_org_id(org_id: Optional[object]) -> Optional[str]:
    """Map an organization id to a sender tenant key, or None."""
    if not org_id:
        return None
    if str(org_id).strip().lower() == CTM_ORG_ID:
        return "ctm"
    return None


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


def sender_for(
    host: Optional[str] = None,
    redirect_url: Optional[str] = None,
    org_id: Optional[object] = None,
) -> Sender:
    """The (display name, from address, reply-to) for one message.

    Resolution order, highest precedence first:

      1. `org_id` — a caller that already knows the tenant is authoritative.
      2. `host` — a bare hostname, when a caller has one directly.
      3. `redirect_url` — the magic-link redirect, whose host names the
         product; this is what the auth mailer actually has at send time.
      4. Nothing recognised -> the MADFAM default.

    The resolved address is then gated on `RESEND_VERIFIED_DOMAINS`: an
    unverified domain is downgraded to the default address, keeping the tenant
    display name. That gate is not optional and not bypassable from a caller —
    see the module docstring for why.
    """
    tenant = _tenant_for_org_id(org_id)
    if tenant is None and host:
        tenant = _tenant_for_host(host)
    if tenant is None and redirect_url:
        tenant = _tenant_for_host(urlparse(redirect_url).hostname)

    if tenant is None:
        return _default_sender()

    sender = _TENANT_SENDERS[tenant]
    if not is_verified_domain(sender[1]):
        return _fallback_for(sender)
    return sender


def sender_for_address(
    from_email: Optional[str],
    from_name: Optional[str] = None,
    host: Optional[str] = None,
    redirect_url: Optional[str] = None,
    org_id: Optional[object] = None,
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
    """
    if from_email and is_verified_domain(from_email):
        name = from_name or _default_sender()[0]
        return name, from_email.strip(), from_email.strip()

    name, address, reply_to = sender_for(host=host, redirect_url=redirect_url, org_id=org_id)
    if from_name:
        name = from_name
    return name, address, reply_to
