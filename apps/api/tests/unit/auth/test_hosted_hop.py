"""The hosted hop: which magic links must land on Janua first.

THE DEFECT THIS GUARDS. Estate SSO is the `janua_sso` cookie, `Domain=.madfam.io`.
Products get it onto the browser by RELAYING janua's `Set-Cookie` line, and a
browser only accepts that relay when the cookie's domain covers the app's host.
`map.creatumundo.mx` is outside `.madfam.io`, so on the client's own brand hosts
the estate cookie can NEVER be minted by a magic-link login — the ERP's
`prompt=none` answers `login_required` and the person is asked for a second
email. No configuration fixes that; the link has to land on janua first.

THE RULE MUST MATCH ITS TYPESCRIPT TWIN. `domain_covers_host` here and
`domainCoversHost` in `@madfam/janua-next` decide the two halves of the same
question: janua uses it to decide whether to mail a product link, the package
uses it to decide whether the cookie may be relayed. If they ever disagreed,
janua would mail a direct link for a host whose relay silently refuses — which
is exactly the live failure on the brand hosts. The label-boundary and
single-label cases below are pinned in both suites for that reason.
"""

import pytest

from app.auth.hosted_hop import (
    domain_covers_host,
    redirect_can_receive_sso_cookie,
    should_use_hosted_hop,
)


class TestDomainCoversHost:
    """Behavioural parity with `domainCoversHost` in @madfam/janua-next."""

    @pytest.mark.parametrize(
        "domain,host",
        [
            (".madfam.io", "crea-map.madfam.io"),
            ("madfam.io", "crea-map.madfam.io"),  # leading dot insignificant
            (".madfam.io", "madfam.io"),  # exact match
            (".madfam.io", "CREA-MAP.MADFAM.IO"),  # case-insensitive
            (".madfam.io", "crea-map.madfam.io:3000"),  # port is not in scope
            (".madfam.io", "deep.nested.madfam.io"),
        ],
    )
    def test_covered(self, domain, host):
        assert domain_covers_host(domain, host) is True

    @pytest.mark.parametrize(
        "domain,host",
        [
            # THE CASE THE WHOLE LANE EXISTS FOR.
            (".madfam.io", "map.creatumundo.mx"),
            (".madfam.io", "erp.creatumundo.mx"),
            # A bare `endswith` would wrongly accept this one.
            (".madfam.io", "notmadfam.io"),
            (".madfam.io", "evil-madfam.io"),
            # A single-label scope is a TLD, never a legitimate cookie domain.
            (".io", "crea-map.madfam.io"),
            ("io", "madfam.io"),
            # Nothing to decide with.
            (None, "crea-map.madfam.io"),
            ("", "crea-map.madfam.io"),
            (".madfam.io", None),
            (".madfam.io", ""),
        ],
    )
    def test_not_covered(self, domain, host):
        assert domain_covers_host(domain, host) is False


class TestRedirectCanReceiveSsoCookie:
    def test_host_inside_the_cookie_domain_can(self, monkeypatch):
        from app.auth import hosted_hop

        monkeypatch.setattr(hosted_hop.settings, "COOKIE_DOMAIN", ".madfam.io", raising=False)
        assert redirect_can_receive_sso_cookie("https://crea-map.madfam.io/api/auth/magic-verify")

    def test_brand_host_cannot(self, monkeypatch):
        from app.auth import hosted_hop

        monkeypatch.setattr(hosted_hop.settings, "COOKIE_DOMAIN", ".madfam.io", raising=False)
        assert not redirect_can_receive_sso_cookie("https://map.creatumundo.mx/api/auth/magic-verify")

    def test_no_cookie_domain_configured_means_nobody_can(self, monkeypatch):
        """With no COOKIE_DOMAIN there is no estate cookie to relay at all."""
        from app.auth import hosted_hop

        monkeypatch.setattr(hosted_hop.settings, "COOKIE_DOMAIN", None, raising=False)
        assert not redirect_can_receive_sso_cookie("https://crea-map.madfam.io/x")

    def test_unparsable_destination_cannot(self, monkeypatch):
        from app.auth import hosted_hop

        monkeypatch.setattr(hosted_hop.settings, "COOKIE_DOMAIN", ".madfam.io", raising=False)
        assert not redirect_can_receive_sso_cookie("not-a-url")


class TestShouldUseHostedHop:
    @pytest.fixture(autouse=True)
    def _cookie_domain(self, monkeypatch):
        from app.auth import hosted_hop

        monkeypatch.setattr(hosted_hop.settings, "COOKIE_DOMAIN", ".madfam.io", raising=False)

    def test_brand_host_takes_the_hop(self):
        """The reason this lane exists: no other path can give them the cookie."""
        assert should_use_hosted_hop("https://map.creatumundo.mx/api/auth/magic-verify") is True
        assert should_use_hosted_hop("https://erp.creatumundo.mx/portal/verify") is True

    def test_estate_host_keeps_todays_direct_link(self):
        """BLAST RADIUS. Every host that works today must keep the byte-identical
        path it uses today — a regression here is a live clinical outage, while a
        regression on the brand hosts is a regression of something not yet live."""
        assert should_use_hosted_hop("https://crea-map.madfam.io/api/auth/magic-verify") is False
        assert should_use_hosted_hop("https://crea-erp.madfam.io/portal/verify") is False

    def test_no_destination_keeps_the_historical_fallback(self):
        """A link with nowhere to forward already lands on janua's callback;
        there is no hop decision to make."""
        assert should_use_hosted_hop(None) is False

    def test_unconfigured_cookie_domain_never_hops(self, monkeypatch):
        """AN UNSET `COOKIE_DOMAIN` IS NOT "OUTSIDE THE ESTATE".

        `COOKIE_DOMAIN` defaults to None, and with it unset
        `redirect_can_receive_sso_cookie` is False for EVERY host — truthfully,
        because there is no estate cookie for anyone to relay. Deriving the hop
        from that would move every magic link in an unconfigured deployment off
        the product host and onto janua's callback: the first-contact failure
        found live mid-ceremony on 2026-08-15, which
        `tests/unit/services/test_magic_link_destination.py` exists to prevent.

        The autouse fixture above pins `.madfam.io` for the rest of this class,
        which is why the rest of the class cannot see this case. It is pinned
        here deliberately.
        """
        from app.auth import hosted_hop

        monkeypatch.setattr(hosted_hop.settings, "COOKIE_DOMAIN", None, raising=False)
        assert should_use_hosted_hop("https://ensayo.madfam.io/portal/verify") is False
        assert should_use_hosted_hop("https://map.creatumundo.mx/api/auth/magic-verify") is False
        # The explicit flag is still an escape hatch, even with no cookie domain.
        assert (
            should_use_hosted_hop("https://ensayo.madfam.io/portal/verify", requested=True) is True
        )
        assert should_use_hosted_hop("") is False

    def test_explicit_flag_wins_in_both_directions(self):
        """The escape hatch is an override, not a one-way opt-in: a covered host
        can be forced onto the hop (a rehearsal), and an uncovered one forced
        off it (a product that has its own answer)."""
        assert should_use_hosted_hop("https://crea-map.madfam.io/x", requested=True) is True
        assert should_use_hosted_hop("https://map.creatumundo.mx/x", requested=False) is False

    def test_flag_cannot_conjure_a_destination(self):
        """`hosted_hop=True` with nowhere to forward is still nowhere to forward."""
        assert should_use_hosted_hop(None, requested=True) is False
