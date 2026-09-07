"""Phase-2 sender resolution, and the verified-domain gate that makes it safe.

Context: docs/EMAIL_SENDER_POLICY.md and app/services/email_sender.py. Phase 1
kept ONE sender for every message; Phase 2 lets a tenant whose own domain we
manage send from it. The thing that must not break is deliverability: Resend
REJECTS a send from an unverified domain, so an unverified sender is not a
message in spam, it is no message at all — and the message is a sign-in link.

The load-bearing guarantees, each with a test that fails loudly if it breaks:

  * no tenant signal -> the MADFAM default, unchanged
  * a CTM signal with `creatumundo.mx` UNVERIFIED -> CTM's NAME on MADFAM's
    ADDRESS (the brand ships early, the deliverability risk never does)
  * a CTM signal with `creatumundo.mx` VERIFIED -> CTM's own address + reply-to
  * a caller-supplied `from_email` on an unverified domain is DISCARDED
  * the sender host table cannot drift from the body-branding host table

Style follows tests/unit/services/test_email_branding.py: patch settings on the
module under test rather than standing up a live provider.
"""

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
    def test_ctm_hosts_before_verification_keep_name_lose_address(self, host):
        with verified("madfam.io"):
            name, address, reply_to = sender_for(host=host)
        assert name == "Crea Tu Mundo"
        assert address == "hola@madfam.io"
        assert reply_to == "hola@madfam.io"

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

    def test_unverified_explicit_address_still_keeps_the_display_name(self):
        """Naming yourself is harmless; claiming a domain is not."""
        with verified("madfam.io"):
            name, address, _ = sender_for_address(from_email="x@attacker.test", from_name="Dhanam")
        assert (name, address) == ("Dhanam", "hola@madfam.io")

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
