"""May this tenant send from its own domain? The vCTO gate.

Owner directive, 2026-09-06: «this type of treatment should be left exclusively
for our vCTO clients, where we have full operational control.»

A branded From line is an operational commitment, not a cosmetic one. When mail
leaves as `Crea Tu Mundo <hola@creatumundo.mx>`, MADFAM has taken on that
domain's DNS, its DKIM rotation, its reputation and its bounce handling. That
is a thing we can promise for a retained client whose infrastructure we run. It
is not a thing we can promise for a self-serve signup, and promising it there
means a stranger's deliverability failure arrives as our incident. So the
branded sender is gated on the commercial relationship.

WHERE THE TIER COMES FROM, AND WHY NOT NAUTA

The task framing offered two sources: (a) a janua-side flag, or (b) nauta's
`Workspace.tier` read over an internal endpoint, with (b) preferred. Reading
nauta first settled it the other way, on three findings:

  1. **Nauta has the tier but exposes it to nobody.** `Workspace.tier` is a
     `ClientTier` enum (`SELF_SERVE | PROJECT | FRACTIONAL_CTO`) and vCTO is
     `FRACTIONAL_CTO`. It is reachable only through human-session tRPC admin
     mutations. Nauta's two machine-authenticated routes are
     `/api/internal/resolve-host` (returns `{workspaceId, provisioning, locale}`
     and its own comment says it "returns the id — never anything inside the
     workspace") and a write-only coupler time-draft route. There is no
     endpoint to call.

  2. **The call would run the wrong way.** Today the integration is strictly
     nauta -> janua: nauta holds `JANUA_SERVICE_TOKEN` and calls janua for
     branding, members, magic links and entitlements. Janua calls nauta
     nowhere. Option (b) would make the identity provider depend on a
     downstream product at send time, in a BackgroundTask with no session and
     no retry budget, for a sign-in link.

  3. **It would contradict the ratified boundary.** Nauta's ADR-0001 and its
     own `erp-catalog.ts` state that «janua is the sole entitlement authority;
     nothing here decides who may see what.» "Is this client entitled to a
     branded sender" is an entitlement question by that definition, so asking
     nauta would invert the very rule nauta is written to respect.

So the source of truth is janua's OWN entitlement store: the
`product_tiers` JSONB on `Organization`, which already has admin grant/revoke
endpoints (`/api/v1/admin/entitlements/org`, audited) and already feeds the
`madfam_entitled_products` JWT claim through `entitlements_service`. The vCTO
relationship becomes one more product tier:

    product_tiers = {"janua": "...", "vcto": "fractional_cto"}

That is not a second registry — it is the registry janua already has, which is
exactly the objection that made option (a) unattractive. Nauta remains free to
render `FRACTIONAL_CTO`; it simply is not the authority for it, which is what
its own ADR says.

WHY THERE IS ALSO A CACHED FALLBACK

The mailer has no DB session. `EmailService()` is constructed inside a FastAPI
BackgroundTask with neither Redis nor a DB handle, so the authoritative read
cannot happen on the send path — the same constraint that put branding on the
redirect host in the first place. The gate therefore has two tiers:

    1. An explicit, caller-supplied decision (`vcto_entitled=True/False`), for
       any caller that DOES hold a session and has already read the tier. This
       is the authoritative path and it is what `refresh_vcto_cache` feeds.
    2. A process-local cache of tenant -> entitled, refreshed by any code path
       that reads the DB (see `refresh_vcto_cache`), consulted when no explicit
       decision was passed.

FAIL CLOSED. When neither tier answers — cold process, unknown tenant, DB
unreachable — the tenant is NOT entitled and the sender falls back to MADFAM's.
"Fail closed" here means the mail still goes out, from `hola@madfam.io`, with
the tenant's display name intact. It never means the sign-in link fails to
arrive: a mail nobody receives is a worse failure than a mail from the platform
address, and the entire verified-domain gate in `email_sender` exists because
of that ordering.

The one deliberate exception is the SEED below.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

import structlog

from app.services.sender_binding import PLATFORM_TENANT

logger = structlog.get_logger()

#: The product slug under which the vCTO relationship is recorded in an
#: organization's `product_tiers`. Free-text by the admin API's own schema
#: (`AdminOrgEntitlementGrantRequest.product`), so this constant is the only
#: place the spelling is decided.
VCTO_PRODUCT = "vcto"

#: Tier values on `VCTO_PRODUCT` that count as an active vCTO engagement.
#: `fractional_cto` mirrors nauta's `ClientTier.FRACTIONAL_CTO` so the two
#: vocabularies read the same even though janua is the authority; `vcto` is
#: accepted as the obvious shorthand an operator will type. Compared
#: lowercased. A tier outside this set — including nauta's `SELF_SERVE` and
#: `PROJECT` — is NOT entitled.
VCTO_TIERS = frozenset({"fractional_cto", "vcto", "fractional-cto"})

# --------------------------------------------------------------------------
# The seed.
#
# WHY THIS EXISTS AND WHY IT IS NOT A BACKDOOR. A cold process has an empty
# cache and no session, so a strict fail-closed gate would send every CTM
# message from hola@madfam.io until something happened to warm it — which for
# the auth mailer is "never", because the auth mailer never touches the DB.
# The gate would then be indistinguishable from having no branded sender at
# all, and #603's shipped behaviour would silently regress.
#
# CTM is a signed vCTO client (contract executed 2026-08-16) and is the tenant
# this whole feature was built for, so its entitlement is asserted here rather
# than discovered. This is a STATEMENT OF THE COMMERCIAL FACT, versioned in
# git, reviewable in a PR, and revocable by deleting one line — not a bypass:
# an explicit `vcto_entitled=False` from a caller that DID read the DB still
# overrides it (see `is_vcto_entitled`), so the day CTM's engagement ends, the
# authoritative read wins over this seed.
#
# A SECOND CLIENT DOES NOT GO HERE. They get an org entitlement grant through
# the audited admin endpoint, and the cache path picks it up. This seed is not
# the mechanism; it is CTM's bridge until a mailer carries a session.
# --------------------------------------------------------------------------
_SEED_ENTITLED: Dict[str, bool] = {
    "ctm": True,
}

# Process-local cache: tenant -> entitled. Guarded by a lock because uvicorn
# workers run BackgroundTasks on a threadpool, and a dict swap under concurrent
# refresh is the kind of thing that works in every test and fails once a month
# in production.
_cache: Dict[str, bool] = dict(_SEED_ENTITLED)
_cache_lock = threading.Lock()


def product_tiers_grant_vcto(product_tiers: Optional[Dict[str, object]]) -> bool:
    """True when an organization's `product_tiers` records an active vCTO tier.

    The single place the JSONB is interpreted, so the admin API, the cache
    refresh and the tests cannot disagree about what "is a vCTO client" means.
    """
    if not product_tiers:
        return False
    tier = product_tiers.get(VCTO_PRODUCT)
    if tier is None:
        return False
    return str(tier).strip().lower() in VCTO_TIERS


def refresh_vcto_cache(tenant: str, entitled: bool) -> None:
    """Record an AUTHORITATIVE entitlement decision for a tenant.

    Called by any code path that has a DB session and has read the org's
    `product_tiers` — the admin grant/revoke endpoints, or a future mailer that
    carries a session. The send path then reads the result without a query.

    An explicit `False` is recorded exactly like a `True`: revocation has to
    propagate as fast as a grant, and leaving the old `True` in place because
    "we only cache positives" is how a concluded engagement keeps sending from
    a domain we no longer run.
    """
    if not tenant:
        return
    with _cache_lock:
        _cache[tenant] = bool(entitled)
    logger.info(
        "sender_policy.vcto_cache_updated",
        tenant=tenant,
        entitled=bool(entitled),
    )


def clear_vcto_cache() -> None:
    """Reset the cache to its seeded state. For tests and operator tooling."""
    with _cache_lock:
        _cache.clear()
        _cache.update(_SEED_ENTITLED)


def is_vcto_entitled(
    tenant: Optional[str],
    vcto_entitled: Optional[bool] = None,
) -> bool:
    """May this tenant use a branded sender?

    Precedence, highest first:

      1. `vcto_entitled` — an explicit decision from a caller that read the
         authoritative store. Honoured in BOTH directions: an explicit False
         overrides the seed, which is what makes the seed revocable at runtime
         rather than only at deploy.
      2. The process cache, seeded with the signed vCTO clients and refreshed
         by `refresh_vcto_cache`.
      3. Not entitled. Fail closed.

    The platform tenant is never "entitled": MADFAM sending as MADFAM is the
    default, not a branded privilege, and answering True here would make the
    fallback path look like a granted one in logs.
    """
    if not tenant or tenant == PLATFORM_TENANT:
        return False
    if vcto_entitled is not None:
        return bool(vcto_entitled)
    with _cache_lock:
        return bool(_cache.get(tenant, False))
