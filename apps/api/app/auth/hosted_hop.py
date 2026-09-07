"""WHEN A MAGIC LINK MUST LAND ON JANUA FIRST (the hosted hop, J6).

## The defect this exists to close

Estate SSO is one cookie: `janua_sso`, `Domain=.madfam.io`, minted by
`_set_session_cookies` and read only by `/authorize` + `/consent`. A person who
holds it is recognised silently at every sibling host (`prompt=none` returns a
code instead of `login_required`).

Products do not sign people in through a browser hop today. They exchange the
magic link SERVER-TO-SERVER — `POST /api/v1/auth/magic-link/verify` from their
Next process — and janua's `Set-Cookie` lands on a `fetch` response Node drops.
`@madfam/janua-next` closes that by RELAYING janua's `Set-Cookie` line verbatim
onto the 303 the app returns to the browser.

That relay has a hard precondition, and it is the whole reason this module
exists: a cookie is only relayable when its `Domain` covers the app's host. A
subdomain may set its parent's cookie, so `crea-map.madfam.io` may emit
`Domain=.madfam.io`. But `map.creatumundo.mx` may not, and no configuration
change can make it: a browser rejects a `.madfam.io` cookie from a
`creatumundo.mx` page outright. On the client's own brand hosts the estate
cookie can NEVER be minted by a magic-link login, so the ERP's `prompt=none`
always answers `login_required` and the person is asked for a second email.

## The fix, and why it is shaped this way

When the destination cannot receive the estate cookie by relay, the emailed link
points at JANUA instead of at the product. The person's browser then visits
`auth.madfam.io` for one hop, which is the one moment the issuer can set its own
first-party cookie, and janua forwards to the product with the `?token=` contract
the products already expect. Nothing about the product-side contract changes.

## Why per-host rather than always

Routing every magic link in the estate through the hop would change the login
path of every product on the day this promotes — including the ones that work.
The per-host rule leaves each host that works today on the byte-identical path it
uses today, and lights the new one only for hosts that are provably broken.

The rule is DERIVED, not configured: it asks the same question the relay guard in
`@madfam/janua-next` asks (`domainCoversHost`). Because both sides compute the
same predicate from the same cookie domain, they cannot disagree, and there is no
host list to keep in sync. It is also self-healing at cutover — when
`map.creatumundo.mx` goes live its links take the hop with no deploy, and a host
that later moved under the cookie domain would revert with no deploy either.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from app.config import settings


def domain_covers_host(cookie_domain: Optional[str], host: Optional[str]) -> bool:
    """Can a cookie scoped to `cookie_domain` be presented to `host`?

    The Python twin of `domainCoversHost` in `@madfam/janua-next`
    (`packages/janua-next/src/magic-verify.ts`). Kept behaviourally identical on
    purpose: this predicate decides whether janua mails a product link, and that
    one decides whether the product may relay the cookie. If the two ever
    disagreed, janua would mail a direct link for a host whose relay silently
    refuses — exactly the failure that is live on the brand hosts today.

    A leading dot is insignificant (`.madfam.io` == `madfam.io`) and a port is
    not part of a cookie's domain scope, so both are normalised away. Matching
    is on a LABEL BOUNDARY: `notmadfam.io` must not match `madfam.io`, which a
    bare `endswith` would wrongly accept.

    SCOPE, HONESTLY STATED: this is not a public-suffix check, matching the
    scope its TypeScript twin documents. A single-label scope (`.io`) is refused
    because it can never legitimately parent anything; a registry-level suffix
    with a dot (`.co.uk`) would pass. Browsers reject both outright and janua is
    a first-party issuer we control, so shipping the PSL for that residue would
    be weight without a threat.
    """
    if not cookie_domain or not host:
        return False
    scope = cookie_domain.strip().lower().lstrip(".").rstrip(".")
    bare = host.strip().lower().split(":")[0].rstrip(".")
    if not scope or not bare:
        return False
    # A single-label scope is a TLD, never a legitimate cookie domain.
    if "." not in scope:
        return False
    return bare == scope or bare.endswith(f".{scope}")


def redirect_can_receive_sso_cookie(redirect_url: Optional[str]) -> bool:
    """Would a product on `redirect_url` be able to relay `janua_sso`?

    False when there is no destination, no parsable host, or no configured
    `COOKIE_DOMAIN` — in every one of those cases the product cannot end up
    holding the estate cookie, which is precisely when the hop earns its keep.
    """
    if not redirect_url:
        return False
    host = urlparse(redirect_url).hostname
    return domain_covers_host(settings.COOKIE_DOMAIN, host)


def should_use_hosted_hop(
    redirect_url: Optional[str],
    *,
    requested: Optional[bool] = None,
) -> bool:
    """Should this magic link land on janua first?

    `requested` is the caller's explicit `hosted_hop` flag and wins in BOTH
    directions when supplied — a product can opt a covered host in (a rehearsal
    host, a future tenant zone) or opt an uncovered host out. It is an escape
    hatch, never the mechanism: the default is derived, so the common case needs
    no configuration and cannot drift.

    With no flag, the hop fires exactly when the destination could not otherwise
    receive the estate cookie.

    A link with NO destination at all keeps its historical behaviour — it
    already lands on janua's own callback (there is nowhere else to send it), so
    this returns False and the existing fallback in `send_magic_link_email`
    builds the same URL it always did.

    NO `COOKIE_DOMAIN` AT ALL IS NOT A REASON TO HOP, and the distinction is the
    difference between a fix and an estate-wide regression. `COOKIE_DOMAIN`
    defaults to None, and `redirect_can_receive_sso_cookie` answers False for
    every host when it is unset — truthfully, since with no cookie domain there
    is no estate cookie for anyone to relay. But "estate SSO is not configured
    here" is a DIFFERENT fact from "this host is provably outside the estate",
    and only the second one is what the hop was built for. Deriving the hop from
    the first would silently move EVERY magic link in an unconfigured
    deployment — dev, a bare test env, any operator who has not run B3 — off the
    product host and onto janua's callback, which is precisely the first-contact
    failure `tests/unit/services/test_magic_link_destination.py` exists to
    prevent (found live mid-ceremony, 2026-08-15). So the hop requires a
    configured cookie domain that demonstrably does NOT cover the destination.
    Prod and staging both set `COOKIE_DOMAIN=.madfam.io`
    (`k8s/base/deployments/janua-api.yaml`), so this guard costs the brand hosts
    nothing; it only refuses to guess where there is no estate to be outside of.
    """
    if not redirect_url:
        return False
    if requested is not None:
        return requested
    if not settings.COOKIE_DOMAIN:
        return False
    return not redirect_can_receive_sso_cookie(redirect_url)
