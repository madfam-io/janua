"""Phase-2 sender resolution, and the verified-domain gate that makes it safe.

Context: docs/EMAIL_SENDER_POLICY.md and app/services/email_sender.py. Phase 1
kept ONE sender for every message; Phase 2 lets a tenant whose own domain we
manage send from it. The thing that must not break is deliverability: Resend
REJECTS a send from an unverified domain, so an unverified sender is not a
message in spam, it is no message at all — and the message is a sign-in link.

The load-bearing guarantees, each with a test that fails loudly if it breaks:

  * no tenant signal -> the MADFAM default, unchanged
  * a CTM signal with `creatumundo.mx` UNVERIFIED -> the PLATFORM sender WHOLE,
    `MADFAM <hola@madfam.io>` (reversed 2026-09-07: this used to be CTM's NAME
    on MADFAM's ADDRESS, and that header reached a production inbox)
  * a CTM signal with `creatumundo.mx` VERIFIED -> CTM's own address + reply-to
  * a caller-supplied `from_email` on an unverified domain is DISCARDED, and
    since 2026-09-07 so is the `from_name` that came with it
  * THE INVARIANT: no From line ever pairs a tenant display name with an
    address on the platform's domain — see `TestDisplayNameFollowsAddress`
  * the sender host table cannot drift from the body-branding host table

Style follows tests/unit/services/test_email_branding.py: patch settings on the
module under test rather than standing up a live provider.
"""

from email.utils import formataddr
from unittest.mock import patch

import pytest

from app.services import email_sender as sender_module
from app.services.email_branding import CTM_HOSTS, CTM_ORG_ID
from app.services.email_sender import (
    SENDER_HOSTS,
    domain_of,
    is_verified_domain,
    sender_for,
    sender_for_address,
)

CTM_REDIRECT = "https://crea-map.madfam.io/portal/verify?next=/"
MADFAM = ("MADFAM", "hola@madfam.io", "hola@madfam.io")


def verified(*domains):
    """Patch RESEND_VERIFIED_DOMAINS for the duration of a with-block."""
    return patch.object(sender_module.settings, "RESEND_VERIFIED_DOMAINS", ",".join(domains))


# --------------------------------------------------------------------------
# The gate itself
# --------------------------------------------------------------------------
class TestVerifiedDomainGate:
    def test_default_verified_set_is_madfam_only(self):
        """The shipped default must NOT include creatumundo.mx: the code lands
        before the domain is verified, and the cutover is a manifest edit."""
        from app.config import Settings

        assert Settings().resend_verified_domains_list == ["madfam.io"]

    def test_blank_config_falls_back_to_madfam_not_empty(self):
        """An empty set would disable EVERY sender and silently stop all mail,
        which is the exact failure this gate exists to prevent."""
        with patch.object(sender_module.settings, "RESEND_VERIFIED_DOMAINS", "   "):
            assert is_verified_domain("hola@madfam.io") is True

    def test_list_is_parsed_case_insensitively_and_trimmed(self):
        with verified("MADFAM.IO", " creatumundo.mx "):
            assert is_verified_domain("hola@madfam.io") is True
            assert is_verified_domain("hola@CreaTuMundo.mx") is True

    def test_subdomain_of_a_verified_domain_is_not_verified(self):
        """Exact match, not suffix: Resend verifies each sending domain
        separately, and a suffix rule would let `evil.madfam.io` through."""
        with verified("madfam.io"):
            assert is_verified_domain("x@evil.madfam.io") is False
            assert is_verified_domain("x@notmadfam.io") is False

    @pytest.mark.parametrize("bad", [None, "", "no-at-sign", "@", "trailing@"])
    def test_malformed_addresses_are_never_verified(self, bad):
        with verified("madfam.io"):
            assert is_verified_domain(bad) is False

    def test_domain_of(self):
        assert domain_of("Hola@MadFam.IO") == "madfam.io"
        assert domain_of("nope") == ""
        assert domain_of(None) == ""


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------
class TestSenderFor:
    def test_no_signal_is_madfam(self):
        with verified("madfam.io"):
            assert sender_for() == MADFAM

    def test_unknown_host_is_madfam(self):
        with verified("madfam.io"):
            assert sender_for(redirect_url="https://example.test/go?t=1") == MADFAM
            assert sender_for(host="example.test") == MADFAM

    def test_madfam_own_host_stays_madfam(self):
        """madfam.io is MADFAM's own host and must not resolve to a tenant."""
        with verified("madfam.io"):
            assert sender_for(host="app.madfam.io") == MADFAM

    @pytest.mark.parametrize(
        "host",
        [
            "crea-map.madfam.io",
            "ensayo-map.madfam.io",
            "kalya.app",
            "app.kalya.app",
            "creatumundo.mx",
            "map.creatumundo.mx",
            "erp.creatumundo.mx",
        ],
    )
    def test_ctm_hosts_before_verification_are_the_platform_sender_whole(self, host):
        """The 2026-09-07 rule: the display name follows the address.

        This test used to assert `("Crea Tu Mundo", "hola@madfam.io")` — the
        deliberately partial downgrade #603 shipped. On 2026-09-07 02:32:21
        CDMX the first magic link from `map.creatumundo.mx` arrived in the CTM
        inbox with exactly that From, and it was rejected: only MADFAM sends
        from `hola@madfam.io`, so a client's name must never sit in front of
        it. Name and address are now one decision.
        """
        with verified("madfam.io"):
            resolved = sender_for(host=host)
        assert resolved == MADFAM
        assert resolved[0] != "Crea Tu Mundo"

    @pytest.mark.parametrize("host", ["creatumundo.mx", "map.creatumundo.mx", "crea-map.madfam.io"])
    def test_ctm_hosts_after_verification_use_the_client_domain(self, host):
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_for(host=host) == (
                "Crea Tu Mundo",
                "hola@creatumundo.mx",
                "hola@creatumundo.mx",
            )

    def test_lookalike_host_does_not_match(self):
        """Dot-boundary suffix matching, inherited from email_branding."""
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_for(host="notcreatumundo.mx") == MADFAM
            assert sender_for(host="evilkalya.app") == MADFAM

    def test_redirect_url_host_is_read(self):
        with verified("madfam.io", "creatumundo.mx"):
            name, address, _ = sender_for(redirect_url=CTM_REDIRECT)
        assert (name, address) == ("Crea Tu Mundo", "hola@creatumundo.mx")

    def test_org_id_resolves_ctm(self):
        with verified("madfam.io", "creatumundo.mx"):
            name, address, _ = sender_for(org_id=CTM_ORG_ID)
        assert (name, address) == ("Crea Tu Mundo", "hola@creatumundo.mx")

    def test_org_id_takes_precedence_over_host(self):
        with verified("madfam.io", "creatumundo.mx"):
            name, _, _ = sender_for(host="example.test", org_id=CTM_ORG_ID)
        assert name == "Crea Tu Mundo"

    def test_host_takes_precedence_over_redirect_url(self):
        with verified("madfam.io", "creatumundo.mx"):
            name, _, _ = sender_for(host="creatumundo.mx", redirect_url="https://x.test/a")
        assert name == "Crea Tu Mundo"


# --------------------------------------------------------------------------
# The internal door: a caller-supplied From
# --------------------------------------------------------------------------
class TestSenderForAddress:
    def test_verified_explicit_address_is_honoured(self):
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_for_address(
                from_email="facturas@creatumundo.mx", from_name="Facturación"
            ) == ("Facturación", "facturas@creatumundo.mx", "facturas@creatumundo.mx")

    def test_unverified_explicit_address_is_discarded(self):
        """A service asking to send as an unverified domain would hand Resend a
        rejection. The From is dropped; the host rule decides instead."""
        with verified("madfam.io"):
            name, address, _ = sender_for_address(from_email="ceo@attacker.test")
        assert address == "hola@madfam.io"
        assert name == "MADFAM"

    def test_unverified_explicit_address_loses_the_display_name_too(self):
        """Reversed 2026-09-07. The old rule was "naming yourself is harmless;
        claiming a domain is not", and it is what let a display name and an
        address be assembled from two individually harmless halves into
        `Crea Tu Mundo <hola@madfam.io>`. A display name is only harmless
        while it names the party that owns the address underneath it, so it is
        honoured exactly where the address is and nowhere else."""
        with verified("madfam.io"):
            name, address, _ = sender_for_address(from_email="x@attacker.test", from_name="Dhanam")
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    def test_no_explicit_address_falls_through_to_the_tenant_rule(self):
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_for_address(from_email=None, host="creatumundo.mx") == (
                "Crea Tu Mundo",
                "hola@creatumundo.mx",
                "hola@creatumundo.mx",
            )

    def test_explicit_name_overrides_the_tenant_name(self):
        with verified("madfam.io", "creatumundo.mx"):
            name, address, _ = sender_for_address(
                from_email=None, from_name="Crea Tu Mundo · Citas", host="creatumundo.mx"
            )
        assert (name, address) == ("Crea Tu Mundo · Citas", "hola@creatumundo.mx")


# --------------------------------------------------------------------------
# THE 2026-09-07 RULE: the display name follows the address.
#
# `Crea Tu Mundo <hola@madfam.io>` was produced in production on 2026-09-07 at
# 02:32:21 CDMX, on the first magic link requested from `map.creatumundo.mx`.
# Only MADFAM sends from `hola@madfam.io`; a brand name may appear only beside
# that brand's own address. These tests are the regression fence.
# --------------------------------------------------------------------------
FORBIDDEN_FROM = "Crea Tu Mundo <hola@madfam.io>"


class TestDisplayNameFollowsAddress:
    @pytest.mark.parametrize(
        "host",
        ["map.creatumundo.mx", "creatumundo.mx", "erp.creatumundo.mx", "crea-map.madfam.io"],
    )
    def test_ctm_host_before_verification_is_exactly_the_platform_from(self, host):
        """(a) RESEND_VERIFIED_DOMAINS=madfam.io, a CTM host -> the PLATFORM
        From, verbatim, and never the observed production header."""
        with verified("madfam.io"):
            name, address, reply_to = sender_for(host=host)
        assert (name, address, reply_to) == MADFAM
        assert formataddr((name, address)) == "MADFAM <hola@madfam.io>"
        assert formataddr((name, address)) != FORBIDDEN_FROM

    def test_the_redirect_url_path_is_the_same(self):
        """The auth mailer resolves off `redirect_url`, not `host` — the exact
        path the production message took. It must reach the same answer."""
        with verified("madfam.io"):
            name, address, _ = sender_for(
                redirect_url="https://map.creatumundo.mx/portal/verify?next=/"
            )
        assert formataddr((name, address)) == "MADFAM <hola@madfam.io>"

    def test_ctm_after_verification_is_the_brand_on_the_brand_address(self):
        """(b) RESEND_VERIFIED_DOMAINS=madfam.io,creatumundo.mx -> the display
        name and the address move together, to the brand's own domain."""
        with verified("madfam.io", "creatumundo.mx"):
            name, address, reply_to = sender_for(host="map.creatumundo.mx")
        assert formataddr((name, address)) == "Crea Tu Mundo <hola@creatumundo.mx>"
        assert reply_to == "hola@creatumundo.mx"

    def test_a_caller_cannot_reassemble_the_forbidden_header_from_a_name(self):
        """The name-only door. A caller supplying `from_name` with no address
        must not put a tenant name on the platform address either."""
        with verified("madfam.io"):
            name, address, _ = sender_for_address(
                from_email=None, from_name="Crea Tu Mundo", host="map.creatumundo.mx"
            )
        assert formataddr((name, address)) != FORBIDDEN_FROM
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    def test_the_vcto_gate_downgrade_also_takes_the_name(self):
        """The other downgrade path. A tenant that fails the vCTO gate resolves
        to the platform sender whole, not to its own name on our address."""
        with verified("madfam.io", "creatumundo.mx"):
            name, address, _ = sender_for(host="map.creatumundo.mx", vcto_entitled=False)
        assert formataddr((name, address)) != FORBIDDEN_FROM
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    @pytest.mark.parametrize("verified_domains", [("madfam.io",), ("madfam.io", "creatumundo.mx")])
    def test_property_no_binding_ever_pairs_a_tenant_name_with_a_platform_address(
        self, verified_domains
    ):
        """(c) The property, over EVERY binding in the registry and every
        signal that reaches it, in both verification states: whenever the
        resolved address is on the PLATFORM's domain, the resolved display
        name is NOT the tenant's.

        Written as a sweep rather than a CTM-specific assertion so that the
        second client binding inherits the guarantee without a new test.
        """
        platform_domain = domain_of(sender_module._default_sender()[1])
        with verified(*verified_domains):
            for tenant, binding in sender_module.all_bindings().items():
                signals = [{"org_id": binding.org_id}] if binding.org_id else []
                signals += [{"host": h} for h in binding.hosts]
                signals += [{"redirect_url": f"https://{h}/verify"} for h in binding.hosts]
                for signal in signals:
                    for entitled in (None, True, False):
                        name, address, _ = sender_for(vcto_entitled=entitled, **signal)
                        if domain_of(address) == platform_domain:
                            assert name != binding.display_name, (
                                f"{tenant} resolved to "
                                f"{formataddr((name, address))!r} for {signal} — a tenant "
                                "display name on the platform address"
                            )


# --------------------------------------------------------------------------
# Structural invariants
# --------------------------------------------------------------------------
class TestInvariants:
    def test_sender_hosts_are_the_branding_hosts(self):
        """A host that renders the Crea Tu Mundo header must also carry the
        Crea Tu Mundo envelope. Deriving rather than restating the tuple is
        what keeps the two from drifting; this pins the derivation."""
        assert SENDER_HOSTS["ctm"] is CTM_HOSTS

    def test_no_tenant_sender_is_on_an_unrelated_domain(self):
        """Every tenant sender address must be on that tenant's own domain or
        MADFAM's — never a third party's."""
        for _tenant, (_name, address, reply_to) in sender_module._TENANT_SENDERS.items():
            assert domain_of(address)
            assert domain_of(reply_to)
