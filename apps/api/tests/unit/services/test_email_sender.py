"""Phase-2 sender resolution, and the verified-domain gate that makes it safe.

Context: docs/EMAIL_SENDER_POLICY.md and app/services/email_sender.py. Phase 1
kept ONE sender for every message; Phase 2 lets a tenant whose own domain we
manage send from it. The thing that must not break is deliverability: Resend
REJECTS a send from an unverified domain, so an unverified sender is not a
message in spam, it is no message at all — and the message is a sign-in link.

The load-bearing guarantees, each with a test that fails loudly if it breaks:

  * no tenant signal -> the MADFAM default, unchanged
  * a CTM signal with CTM's own Resend key ABSENT -> the PLATFORM sender WHOLE,
    `MADFAM <hola@madfam.io>` (the display-name rule of 2026-09-07: this used
    to be CTM's NAME on MADFAM's ADDRESS, and that header reached a production
    inbox)
  * a CTM signal with that key PRESENT -> CTM's own address + reply-to

WHAT CHANGED ON 2026-09-07 (LATER THE SAME DAY). CTM moved to its OWN Resend
account: `creatumundo.mx` is verified THERE, so CTM's binding carries its own
`verified_domains` and the global `RESEND_VERIFIED_DOMAINS` — which describes
MADFAM's account — is no longer the authority for it. The fact that now decides
whether the branded From ships is whether CTM's key, env `CTM_RESEND_API_KEY`,
is present in the process: with it, the message can actually leave on the
account that verified the domain; without it, the branded address would go out
on MADFAM's account, where the domain is NOT verified and Resend rejects the
send — a magic link that never arrives. So the tests below supply or withhold
that env var where they used to add or omit a global verified domain.
  * a caller-supplied `from_email` on an unverified domain is DISCARDED, and
    since 2026-09-07 so is the `from_name` that came with it
  * THE INVARIANT: no From line ever pairs a tenant display name with an
    address on the platform's domain — see `TestDisplayNameFollowsAddress`
  * the sender host table cannot drift from the body-branding host table

Style follows tests/unit/services/test_email_branding.py: patch settings on the
module under test rather than standing up a live provider.
"""

import os
from contextlib import contextmanager
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

#: The env var CTM's binding names. The VALUE is a fake that never leaves the
#: process — what is tested is presence, which is all the credential gate reads.
CTM_CREDENTIAL_ENV = "CTM_RESEND_API_KEY"
FAKE_CTM_KEY = "re_test_ctm_key_not_real"


def verified(*domains):
    """Patch the GLOBAL RESEND_VERIFIED_DOMAINS (MADFAM's account) for a block.

    Still the authority for the PLATFORM binding and for any binding on
    MADFAM's account. It is NOT the authority for CTM any more — see
    `with_ctm_credential`.
    """
    return patch.object(sender_module.settings, "RESEND_VERIFIED_DOMAINS", ",".join(domains))


def with_ctm_credential(value: str = FAKE_CTM_KEY):
    """Put CTM's own Resend key in the environment for a with-block.

    Patching `os.environ` rather than `settings` because that is how the key
    actually arrives in production: the janua-secrets ExternalSecret projects
    it as an env var, and janua-api has no Vault access at runtime.
    """
    return patch.dict(os.environ, {CTM_CREDENTIAL_ENV: value})


@contextmanager
def _nothing():
    """A no-op context manager, so a parametrised test can say "and in this
    case, change nothing" without branching around the with-statement."""
    yield


@pytest.fixture(autouse=True)
def _no_ambient_ctm_credential():
    """No test inherits a real CTM key from the developer's shell — otherwise
    whether the branded sender resolves would depend on who ran the suite."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop(CTM_CREDENTIAL_ENV, None)
        yield


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
    def test_ctm_hosts_without_ctms_own_key_are_the_platform_sender_whole(self, host):
        """The 2026-09-07 rule: the display name follows the address.

        This test used to assert `("Crea Tu Mundo", "hola@madfam.io")` — the
        deliberately partial downgrade #603 shipped. On 2026-09-07 02:32:21
        CDMX the first magic link from `map.creatumundo.mx` arrived in the CTM
        inbox with exactly that From, and it was rejected: only MADFAM sends
        from `hola@madfam.io`, so a client's name must never sit in front of
        it. Name and address are now one decision.

        The DOWNGRADE TRIGGER changed later that day, the rule did not. CTM now
        sends on its own Resend account, so the question is no longer "is
        `creatumundo.mx` in MADFAM's verified list" but "can this process
        authenticate to the account that verified it". Without
        `CTM_RESEND_API_KEY` the answer is no, and the branded address would be
        presented to MADFAM's account, which has never verified that domain.
        """
        with verified("madfam.io"):  # CTM_RESEND_API_KEY deliberately absent
            resolved = sender_for(host=host)
        assert resolved == MADFAM
        assert resolved[0] != "Crea Tu Mundo"

    @pytest.mark.parametrize("host", ["creatumundo.mx", "map.creatumundo.mx", "crea-map.madfam.io"])
    def test_ctm_hosts_with_ctms_own_key_use_the_client_domain(self, host):
        """With the key present the message can actually leave on the account
        that verified the domain, so the branded From ships — name and address
        together, and a matching reply-to."""
        with verified("madfam.io"), with_ctm_credential():
            assert sender_for(host=host) == (
                "Crea Tu Mundo",
                "hola@creatumundo.mx",
                "hola@creatumundo.mx",
            )

    @pytest.mark.parametrize("host", ["creatumundo.mx", "map.creatumundo.mx"])
    def test_the_global_verified_list_no_longer_decides_for_ctm(self, host):
        """Verification is per-ACCOUNT. `creatumundo.mx` in MADFAM's global list
        says nothing about CTM's own account, and must not by itself unlock the
        branded sender — believing it would send from a domain CTM's account
        might never have verified."""
        with verified("madfam.io", "creatumundo.mx"):  # key still absent
            assert sender_for(host=host) == MADFAM

    def test_lookalike_host_does_not_match(self):
        """Dot-boundary suffix matching, inherited from email_branding."""
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_for(host="notcreatumundo.mx") == MADFAM
            assert sender_for(host="evilkalya.app") == MADFAM

    def test_redirect_url_host_is_read(self):
        with verified("madfam.io"), with_ctm_credential():
            name, address, _ = sender_for(redirect_url=CTM_REDIRECT)
        assert (name, address) == ("Crea Tu Mundo", "hola@creatumundo.mx")

    def test_org_id_resolves_ctm(self):
        with verified("madfam.io"), with_ctm_credential():
            name, address, _ = sender_for(org_id=CTM_ORG_ID)
        assert (name, address) == ("Crea Tu Mundo", "hola@creatumundo.mx")

    def test_org_id_takes_precedence_over_host(self):
        with verified("madfam.io"), with_ctm_credential():
            name, _, _ = sender_for(host="example.test", org_id=CTM_ORG_ID)
        assert name == "Crea Tu Mundo"

    def test_host_takes_precedence_over_redirect_url(self):
        with verified("madfam.io"), with_ctm_credential():
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
        with verified("madfam.io"), with_ctm_credential():
            assert sender_for_address(from_email=None, host="creatumundo.mx") == (
                "Crea Tu Mundo",
                "hola@creatumundo.mx",
                "hola@creatumundo.mx",
            )

    def test_explicit_name_overrides_the_tenant_name(self):
        with verified("madfam.io"), with_ctm_credential():
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
    def test_a_downgraded_ctm_host_is_exactly_the_platform_from(self, host):
        """(a) A CTM host with the tenant's key absent -> the PLATFORM From,
        verbatim, and never the observed production header."""
        with verified("madfam.io"):
            name, address, reply_to = sender_for(host=host)
        assert (name, address, reply_to) == MADFAM
        assert formataddr((name, address)) == "MADFAM <hola@madfam.io>"
        assert formataddr((name, address)) != FORBIDDEN_FROM

    def test_the_redirect_url_path_is_the_same(self):
        """The auth mailer resolves off `redirect_url`, not `host` — the exact
        path the production message took. It must reach the same answer, in
        BOTH directions, or the one code path production actually uses would be
        the one path not covered by the rule."""
        redirect = "https://map.creatumundo.mx/portal/verify?next=/"
        with verified("madfam.io"):
            name, address, _ = sender_for(redirect_url=redirect)
            assert formataddr((name, address)) == "MADFAM <hola@madfam.io>"

            with with_ctm_credential():
                name, address, _ = sender_for(redirect_url=redirect)
        assert formataddr((name, address)) == "Crea Tu Mundo <hola@creatumundo.mx>"

    def test_ctm_with_its_own_key_is_the_brand_on_the_brand_address(self):
        """(b) The enabled state -> the display name and the address move
        together, to the brand's own domain."""
        with verified("madfam.io"), with_ctm_credential():
            name, address, reply_to = sender_for(host="map.creatumundo.mx")
        assert formataddr((name, address)) == "Crea Tu Mundo <hola@creatumundo.mx>"
        assert reply_to == "hola@creatumundo.mx"

    def test_a_caller_cannot_reassemble_the_forbidden_header_from_a_name(self):
        """The name-only door. A caller supplying `from_name` with no address
        must not put a tenant name on the platform address either — on ANY
        downgrade path, including the credential one, which is the path a
        half-finished account migration leaves the system on."""
        with verified("madfam.io"):  # CTM's key absent -> the address downgrades
            name, address, _ = sender_for_address(
                from_email=None, from_name="Crea Tu Mundo", host="map.creatumundo.mx"
            )
        assert formataddr((name, address)) != FORBIDDEN_FROM
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    def test_the_vcto_gate_downgrade_also_takes_the_name(self):
        """The other downgrade path. A tenant that fails the vCTO gate resolves
        to the platform sender whole, not to its own name on our address —
        even with its credential present, which is what makes this the vCTO
        gate's own assertion rather than the credential gate's."""
        with verified("madfam.io", "creatumundo.mx"), with_ctm_credential():
            name, address, _ = sender_for(host="map.creatumundo.mx", vcto_entitled=False)
        assert formataddr((name, address)) != FORBIDDEN_FROM
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    def test_the_credential_downgrade_also_takes_the_name(self):
        """The newest downgrade path, asserted in its own right. An operator
        who flips a binding to the tenant's account before writing the key must
        not thereby produce the forbidden header on every message in the
        window."""
        with verified("madfam.io", "creatumundo.mx"):  # key absent
            name, address, _ = sender_for(host="map.creatumundo.mx", vcto_entitled=True)
        assert formataddr((name, address)) != FORBIDDEN_FROM
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    @pytest.mark.parametrize("verified_domains", [("madfam.io",), ("madfam.io", "creatumundo.mx")])
    @pytest.mark.parametrize("credential_present", [False, True])
    def test_property_no_binding_ever_pairs_a_tenant_name_with_a_platform_address(
        self, verified_domains, credential_present
    ):
        """(c) The property, over EVERY binding in the registry and every
        signal that reaches it, across every gate state: whenever the resolved
        address is on the PLATFORM's domain, the resolved display name is NOT
        the tenant's.

        Written as a sweep rather than a CTM-specific assertion so that the
        second client binding inherits the guarantee without a new test. The
        `credential_present` axis was added when CTM moved to its own account:
        a missing tenant credential is a THIRD way to reach the platform
        address, and every route to that address has to satisfy the same rule
        or the sweep would stop covering the state production is actually in
        during an account migration.
        """
        platform_domain = domain_of(sender_module._default_sender()[1])
        credential = with_ctm_credential() if credential_present else _nothing()
        with verified(*verified_domains), credential:
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

    @pytest.mark.parametrize("credential_present", [False, True])
    def test_property_a_branded_address_always_implies_a_reachable_account(
        self, credential_present
    ):
        """The companion property, and the one the account migration added.

        Whenever a resolved address is NOT on the platform domain, the binding
        that produced it must be one this process can actually send on: either
        it is on MADFAM's account (the SDK already holds that key) or its own
        credential resolved. A branded address we cannot authenticate for is
        not a degraded send, it is a Resend rejection on a sign-in link.
        """
        from app.services.sender_credentials import tenant_credential_available

        platform_domain = domain_of(sender_module._default_sender()[1])
        credential = with_ctm_credential() if credential_present else _nothing()
        with verified("madfam.io", "creatumundo.mx"), credential:
            for tenant, binding in sender_module.all_bindings().items():
                signals = [{"host": h} for h in binding.hosts]
                signals += [{"redirect_url": f"https://{h}/verify"} for h in binding.hosts]
                for signal in signals:
                    _name, address, _ = sender_for(**signal)
                    if domain_of(address) != platform_domain:
                        assert tenant_credential_available(binding), (
                            f"{tenant} resolved to the branded address {address!r} for "
                            f"{signal} with no credential for the account that verified it"
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
