"""Tenant sender bindings: the vCTO gate, per-account verification, portability.

Context: `app/services/sender_binding.py`, `sender_policy.py`,
`sender_credentials.py`, and the owner directive of 2026-09-06 — a branded From
line is for vCTO clients only, and any such client must be able to move to their
own provider account without a code change.

The load-bearing guarantees, each with a test that fails loudly if it breaks:

  * a tenant that is NOT vCTO-entitled keeps its display NAME and loses its
    ADDRESS — the same partial downgrade the verification gate performs
  * the gate FAILS CLOSED: unknown tenant, cold cache, or no answer -> MADFAM
  * an explicit authoritative decision overrides the seed IN BOTH DIRECTIONS,
    so a concluded engagement stops sending from the client's domain
  * a caller-supplied `from_email` on a CLIENT's domain is gated too, or the
    internal API key would be a way around the vCTO restriction
  * verification is per-ACCOUNT: a tenant on its own account reads its own
    verified_domains, not the global RESEND_VERIFIED_DOMAINS
  * a binding that would send on the wrong account is rejected at IMPORT
  * everything #603 shipped still resolves exactly as it did

Style follows tests/unit/services/test_email_sender.py: patch settings on the
module under test rather than standing up a live provider.
"""

import dataclasses
from unittest.mock import patch

import pytest

from app.services import email_sender as sender_module
from app.services.email_branding import CTM_HOSTS
from app.services.sender_binding import (
    ACCOUNT_MADFAM,
    ACCOUNT_TENANT,
    MADFAM_RESEND_CREDENTIAL_REF,
    PLATFORM_BINDING,
    PLATFORM_TENANT,
    PROVIDER_RESEND,
    PROVIDER_SMTP,
    SUPPORTED_ACCOUNTS,
    SUPPORTED_PROVIDERS,
    SenderBinding,
    all_bindings,
    resolve_binding,
    tenant_for_host,
    tenant_for_org_id,
)
from app.services.sender_policy import (
    VCTO_PRODUCT,
    clear_vcto_cache,
    is_vcto_entitled,
    product_tiers_grant_vcto,
    refresh_vcto_cache,
)

CTM_REDIRECT = "https://crea-map.madfam.io/portal/verify?next=/"
MADFAM = ("MADFAM", "hola@madfam.io", "hola@madfam.io")


def verified(*domains):
    """Patch the GLOBAL RESEND_VERIFIED_DOMAINS (MADFAM's account)."""
    return patch.object(sender_module.settings, "RESEND_VERIFIED_DOMAINS", ",".join(domains))


@pytest.fixture(autouse=True)
def _reset_policy_cache():
    """Every test starts from the seeded cache and leaves it that way.

    The cache is process-global by design (the send path has no session), so
    without this a test that revokes CTM would silently change the meaning of
    every test that ran after it.
    """
    clear_vcto_cache()
    yield
    clear_vcto_cache()


# --------------------------------------------------------------------------
# The binding registry
# --------------------------------------------------------------------------
class TestBindingRegistry:
    def test_ctm_binding_is_on_madfam_account_today(self):
        """The shipped state. CTM sends FROM their domain, ON our account —
        moving the account is a separate, deliberate operator action."""
        binding = resolve_binding("ctm")
        assert binding.account == ACCOUNT_MADFAM
        assert binding.credential_ref == MADFAM_RESEND_CREDENTIAL_REF
        assert binding.from_address == "hola@creatumundo.mx"
        assert binding.is_on_tenant_account is False

    def test_unknown_tenant_resolves_to_the_platform_binding(self):
        assert resolve_binding("nobody") is PLATFORM_BINDING
        assert resolve_binding(None) is PLATFORM_BINDING
        assert resolve_binding("") is PLATFORM_BINDING

    def test_platform_binding_is_not_a_client_binding(self):
        """The fallback must not be reachable as a tenant, or a downgrade would
        look like a granted branded sender in logs and in the gate."""
        assert PLATFORM_TENANT not in all_bindings()

    def test_ctm_hosts_are_the_branding_hosts(self):
        """Same object, not a copy: envelope and body cannot drift."""
        assert resolve_binding("ctm").hosts is CTM_HOSTS

    def test_all_bindings_returns_a_copy(self):
        """A caller that mutated the registry would change who every later
        message in this process comes from."""
        snapshot = all_bindings()
        snapshot["injected"] = PLATFORM_BINDING
        assert "injected" not in all_bindings()

    def test_bindings_are_frozen(self):
        """A binding is configuration, not state. Mutation would be a
        cross-request bug in a long-lived worker, where the registry is a
        module-level shared object."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            resolve_binding("ctm").display_name = "Someone Else"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "host,expected",
        [
            ("crea-map.madfam.io", "ctm"),
            ("map.creatumundo.mx", "ctm"),
            ("app.kalya.app", "ctm"),
            ("notcreatumundo.mx", None),
            ("evilkalya.app", None),
            ("madfam.io", None),
            (None, None),
        ],
    )
    def test_tenant_for_host(self, host, expected):
        assert tenant_for_host(host) == expected

    def test_tenant_for_org_id(self):
        assert tenant_for_org_id(resolve_binding("ctm").org_id) == "ctm"
        assert tenant_for_org_id("00000000-0000-0000-0000-000000000000") is None
        assert tenant_for_org_id(None) is None

    def test_redacted_never_carries_a_secret(self):
        """A binding is safe to log: it holds a credential NAME, not a value."""
        redacted = resolve_binding("ctm").redacted()
        # The REFERENCE is present (an operator debugging a switch needs it)...
        assert redacted["credential_ref"] == MADFAM_RESEND_CREDENTIAL_REF
        # ...and no value shaped like a Resend key ever is.
        assert not any(v.startswith("re_") for v in redacted.values())


class TestRegistryValidation:
    """A malformed binding must fail at IMPORT, not on a sign-in link."""

    def _validate(self, binding: SenderBinding):
        from app.services import sender_binding as mod

        with patch.object(mod, "_BINDINGS", {binding.tenant: binding}):
            mod._validate_registry()

    def _ctm_like(self, **overrides) -> SenderBinding:
        base = resolve_binding("ctm")
        fields = {
            "tenant": base.tenant,
            "display_name": base.display_name,
            "from_address": base.from_address,
            "reply_to": base.reply_to,
            "provider": base.provider,
            "account": base.account,
            "credential_ref": base.credential_ref,
            "verified_domains": base.verified_domains,
            "hosts": base.hosts,
            "org_id": base.org_id,
        }
        fields.update(overrides)
        return SenderBinding(**fields)

    def test_the_shipped_registry_validates(self):
        from app.services import sender_binding as mod

        mod._validate_registry()  # must not raise

    def test_unknown_provider_is_rejected(self):
        with pytest.raises(ValueError, match="unknown provider"):
            self._validate(self._ctm_like(provider="carrier-pigeon"))

    def test_unknown_account_is_rejected(self):
        with pytest.raises(ValueError, match="unknown account"):
            self._validate(self._ctm_like(account="somebody-else"))

    def test_tenant_account_may_not_reference_madfams_credential(self):
        """Otherwise the mail goes out on MADFAM's account while the binding
        claims the tenant's — the exact confusion the switch script prevents."""
        with pytest.raises(ValueError, match="still references MADFAM's credential"):
            self._validate(
                self._ctm_like(
                    account=ACCOUNT_TENANT,
                    credential_ref=MADFAM_RESEND_CREDENTIAL_REF,
                    verified_domains=("creatumundo.mx",),
                )
            )

    def test_tenant_account_must_carry_its_own_verified_domains(self):
        """The global list describes MADFAM's account, so on the tenant's own
        account it is the wrong authority and nothing would be sendable."""
        with pytest.raises(ValueError, match="lists no verified_domains"):
            self._validate(
                self._ctm_like(
                    account=ACCOUNT_TENANT,
                    credential_ref="secret/data/janua/senders/ctm#resend_api_key",
                    verified_domains=(),
                )
            )

    def test_a_valid_tenant_account_binding_passes(self):
        self._validate(
            self._ctm_like(
                account=ACCOUNT_TENANT,
                credential_ref="secret/data/janua/senders/ctm#resend_api_key",
                verified_domains=("creatumundo.mx",),
            )
        )

    def test_addresses_must_be_addresses(self):
        with pytest.raises(ValueError, match="from_address is not an address"):
            self._validate(self._ctm_like(from_address="creatumundo.mx"))

    def test_supported_sets_are_what_the_code_branches_on(self):
        assert PROVIDER_RESEND in SUPPORTED_PROVIDERS
        assert PROVIDER_SMTP in SUPPORTED_PROVIDERS
        assert set(SUPPORTED_ACCOUNTS) == {ACCOUNT_MADFAM, ACCOUNT_TENANT}


# --------------------------------------------------------------------------
# The vCTO gate
# --------------------------------------------------------------------------
class TestVctoPolicy:
    def test_ctm_is_seeded_entitled(self):
        """CTM is a signed vCTO client; the seed is what keeps #603's shipped
        behaviour intact on a cold process with no DB session."""
        assert is_vcto_entitled("ctm") is True

    def test_unknown_tenant_fails_closed(self):
        assert is_vcto_entitled("acme") is False

    def test_no_tenant_is_never_entitled(self):
        assert is_vcto_entitled(None) is False
        assert is_vcto_entitled("") is False

    def test_the_platform_tenant_is_never_entitled(self):
        """MADFAM sending as MADFAM is the default, not a branded privilege."""
        assert is_vcto_entitled(PLATFORM_TENANT) is False

    def test_explicit_true_overrides_a_cold_cache(self):
        assert is_vcto_entitled("acme", vcto_entitled=True) is True

    def test_explicit_false_overrides_the_seed(self):
        """The seed is a statement of a commercial fact, not a bypass: an
        authoritative read saying the engagement ended must win."""
        assert is_vcto_entitled("ctm", vcto_entitled=False) is False

    def test_refresh_records_a_grant(self):
        refresh_vcto_cache("acme", True)
        assert is_vcto_entitled("acme") is True

    def test_refresh_records_a_REVOCATION(self):
        """Revocation must propagate as fast as a grant, or a concluded
        engagement keeps sending from a domain we no longer run."""
        assert is_vcto_entitled("ctm") is True
        refresh_vcto_cache("ctm", False)
        assert is_vcto_entitled("ctm") is False

    def test_clear_restores_the_seed(self):
        refresh_vcto_cache("ctm", False)
        clear_vcto_cache()
        assert is_vcto_entitled("ctm") is True

    def test_refresh_ignores_an_empty_tenant(self):
        refresh_vcto_cache("", True)
        assert is_vcto_entitled("") is False


class TestProductTiersInterpretation:
    """`product_tiers` is janua's OWN entitlement store — the source of truth
    for the gate. One place decides what 'is a vCTO client' means."""

    @pytest.mark.parametrize("tier", ["fractional_cto", "FRACTIONAL_CTO", "vcto", " Vcto "])
    def test_vcto_tiers_grant(self, tier):
        assert product_tiers_grant_vcto({VCTO_PRODUCT: tier}) is True

    @pytest.mark.parametrize("tier", ["self_serve", "project", "SELF_SERVE", "pro", ""])
    def test_other_tiers_do_not_grant(self, tier):
        """Nauta's SELF_SERVE and PROJECT are explicitly not vCTO."""
        assert product_tiers_grant_vcto({VCTO_PRODUCT: tier}) is False

    def test_absent_product_does_not_grant(self):
        assert product_tiers_grant_vcto({"enclii": "pro"}) is False
        assert product_tiers_grant_vcto({}) is False
        assert product_tiers_grant_vcto(None) is False


# --------------------------------------------------------------------------
# The gate as seen through the sender
# --------------------------------------------------------------------------
class TestSenderUnderTheVctoGate:
    def test_entitled_ctm_resolves_exactly_as_before(self):
        """#603's behaviour, unchanged: this is the regression guard for the
        whole refactor."""
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_module.sender_for(host="creatumundo.mx") == (
                "Crea Tu Mundo",
                "hola@creatumundo.mx",
                "hola@creatumundo.mx",
            )

    def test_a_non_vcto_tenant_loses_the_name_with_the_domain(self):
        """Reversed 2026-09-07. The downgrade used to be partial — "the brand
        is cosmetic, the address is operational" — and that produced
        `Crea Tu Mundo <hola@madfam.io>` in a production inbox. A display name
        is a claim about who owns the address beside it, so it is exactly as
        operational as the address: both gates now return the platform binding
        whole."""
        with verified("madfam.io", "creatumundo.mx"):
            name, address, reply_to = sender_module.sender_for(
                host="creatumundo.mx", vcto_entitled=False
            )
        assert (name, address, reply_to) == MADFAM

    def test_the_gate_does_not_rescue_an_unverified_domain(self):
        """Both gates apply. Being a vCTO client does not make Resend accept a
        send from a domain it has not verified — and since 2026-09-07 the
        failed gate takes the display name with it."""
        with verified("madfam.io"):
            name, address, _ = sender_module.sender_for(host="creatumundo.mx", vcto_entitled=True)
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    def test_revocation_through_the_cache_moves_the_sender(self):
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_module.sender_for(host="creatumundo.mx")[1] == "hola@creatumundo.mx"
            refresh_vcto_cache("ctm", False)
            assert sender_module.sender_for(host="creatumundo.mx")[1] == "hola@madfam.io"

    def test_no_tenant_signal_is_untouched_by_the_gate(self):
        with verified("madfam.io"):
            assert sender_module.sender_for() == MADFAM
            assert sender_module.sender_for(host="example.test") == MADFAM


class TestCallerSuppliedAddressIsGated:
    """The internal door must not be a way around the vCTO restriction."""

    def test_a_clients_domain_from_an_unentitled_caller_is_discarded(self):
        """The address is discarded, and since 2026-09-07 so is the name that
        came with it: a caller who may not claim the domain may not claim to
        be its owner over MADFAM's address either."""
        with verified("madfam.io", "creatumundo.mx"):
            name, address, _ = sender_module.sender_for_address(
                from_email="facturas@creatumundo.mx",
                from_name="Facturación",
                vcto_entitled=False,
            )
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    def test_a_clients_domain_from_an_entitled_caller_is_honoured(self):
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_module.sender_for_address(
                from_email="facturas@creatumundo.mx", from_name="Facturación"
            ) == ("Facturación", "facturas@creatumundo.mx", "facturas@creatumundo.mx")

    def test_madfams_own_domain_is_never_gated(self):
        """Sending as MADFAM was never the branded privilege."""
        with verified("madfam.io"):
            assert sender_module.sender_for_address(
                from_email="soporte@madfam.io", from_name="Soporte", vcto_entitled=False
            ) == ("Soporte", "soporte@madfam.io", "soporte@madfam.io")

    def test_an_unverified_domain_is_still_discarded(self):
        with verified("madfam.io"):
            _name, address, _ = sender_module.sender_for_address(
                from_email="ceo@attacker.test", vcto_entitled=True
            )
        assert address == "hola@madfam.io"


# --------------------------------------------------------------------------
# Per-account verification — the portability invariant
# --------------------------------------------------------------------------
class TestPerAccountVerification:
    def test_a_madfam_account_binding_reads_the_global_list(self):
        with verified("madfam.io", "creatumundo.mx"):
            assert sender_module.is_verified_domain(
                "hola@creatumundo.mx", binding=resolve_binding("ctm")
            )

    def test_a_tenant_account_binding_reads_its_own_list(self):
        """The global list describes MADFAM's account. Once the tenant sends on
        their own account it is the wrong authority, and trusting it is how you
        send from a domain THEIR account has never verified."""
        moved = SenderBinding(
            tenant="ctm",
            display_name="Crea Tu Mundo",
            from_address="hola@creatumundo.mx",
            reply_to="hola@creatumundo.mx",
            account=ACCOUNT_TENANT,
            credential_ref="secret/data/janua/senders/ctm#resend_api_key",
            verified_domains=("creatumundo.mx",),
        )
        # Global list does NOT contain creatumundo.mx; the binding's does.
        with verified("madfam.io"):
            assert sender_module.is_verified_domain("hola@creatumundo.mx", binding=moved) is True
            # ...and a domain the tenant's account has NOT verified stays out,
            # even though MADFAM's account has it.
            assert sender_module.is_verified_domain("hola@madfam.io", binding=moved) is False

    def test_no_binding_argument_preserves_the_old_signature(self):
        """#603's callers pass one argument; that path must not change."""
        with verified("madfam.io"):
            assert sender_module.is_verified_domain("hola@madfam.io") is True
            assert sender_module.is_verified_domain("hola@creatumundo.mx") is False


class TestBindingForResolution:
    def test_binding_for_follows_the_same_precedence_as_sender_for(self):
        assert sender_module.binding_for(host="creatumundo.mx").tenant == "ctm"
        assert sender_module.binding_for(redirect_url=CTM_REDIRECT).tenant == "ctm"
        assert sender_module.binding_for(host="example.test") is PLATFORM_BINDING

    def test_binding_for_ignores_the_vcto_gate(self):
        """A gated-off tenant sends on the PLATFORM account by definition, so
        the binding view is about the account, not the entitlement."""
        refresh_vcto_cache("ctm", False)
        assert sender_module.binding_for(host="creatumundo.mx").tenant == "ctm"


# --------------------------------------------------------------------------
# Credentials — references in, never values out
# --------------------------------------------------------------------------
class TestSenderCredentials:
    @pytest.mark.asyncio
    async def test_madfam_account_resolves_to_none(self):
        """None means 'change nothing': the SDK is already configured with the
        platform key, so the pre-existing path stays byte-identical."""
        from app.services.sender_credentials import resolve_credential

        assert await resolve_credential(resolve_binding("ctm")) is None

    @pytest.mark.asyncio
    async def test_a_tenant_binding_with_a_missing_credential_raises(self):
        """Loud, not silent: a tenant-account binding that cannot find its key
        must not quietly send on somebody else's account."""
        from app.services.sender_credentials import (
            SenderCredentialError,
            resolve_credential,
        )

        moved = SenderBinding(
            tenant="ctm",
            display_name="Crea Tu Mundo",
            from_address="hola@creatumundo.mx",
            reply_to="hola@creatumundo.mx",
            account=ACCOUNT_TENANT,
            credential_ref="CTM_RESEND_API_KEY_DEFINITELY_NOT_SET",
            verified_domains=("creatumundo.mx",),
        )
        with pytest.raises(SenderCredentialError):
            await resolve_credential(moved)

    @pytest.mark.asyncio
    async def test_an_env_reference_resolves(self, monkeypatch):
        from app.services.sender_credentials import resolve_credential

        monkeypatch.setenv("CTM_TEST_SENDER_KEY", "re_not_a_real_key")
        moved = SenderBinding(
            tenant="ctm",
            display_name="Crea Tu Mundo",
            from_address="hola@creatumundo.mx",
            reply_to="hola@creatumundo.mx",
            account=ACCOUNT_TENANT,
            credential_ref="CTM_TEST_SENDER_KEY",
            verified_domains=("creatumundo.mx",),
        )
        assert await resolve_credential(moved) == "re_not_a_real_key"

    def test_vault_reference_is_split_on_the_field_suffix(self):
        from app.services.sender_credentials import _is_vault_ref, _split_vault_ref

        assert _is_vault_ref("secret/data/janua/senders/ctm#resend_api_key") is True
        assert _is_vault_ref("RESEND_API_KEY") is False
        assert _split_vault_ref("secret/data/janua/senders/ctm#resend_api_key") == (
            "secret/data/janua/senders/ctm",
            "resend_api_key",
        )
        assert _split_vault_ref("secret/data/janua/senders/ctm") == (
            "secret/data/janua/senders/ctm",
            "api_key",
        )


# --------------------------------------------------------------------------
# Structural invariants shared with the #603 modules
# --------------------------------------------------------------------------
class TestInvariants:
    def test_derived_tables_match_the_registry(self):
        """`_TENANT_SENDERS` and `SENDER_HOSTS` are DERIVED views; if they ever
        stop matching the registry, one of them is lying about the sender."""
        for tenant, binding in all_bindings().items():
            assert sender_module._TENANT_SENDERS[tenant] == (
                binding.display_name,
                binding.from_address,
                binding.reply_to,
            )
            assert sender_module.SENDER_HOSTS[tenant] is binding.hosts

    def test_no_binding_sends_from_a_third_party_domain(self):
        """Every sender address is on a domain MADFAM or the client owns.

        Exact match or a DOT-BOUNDARY suffix, never a bare `endswith`: a plain
        suffix test would accept `evilmadfam.io` and `notcreatumundo.mx`, which
        is the same lookalike hole `_host_matches` exists to close on the host
        side. (Flagged by CodeQL py/incomplete-url-substring-sanitization.)
        """
        owned = ("madfam.io", "creatumundo.mx")
        for _tenant, binding in all_bindings().items():
            domain = binding.from_address.rsplit("@", 1)[1].lower()
            assert any(domain == o or domain.endswith("." + o) for o in owned), domain

    def test_every_binding_has_a_credential_reference_not_a_value(self):
        """A binding is versioned configuration in git. A value here would be a
        committed secret."""
        for _tenant, binding in all_bindings().items():
            assert binding.credential_ref
            assert not binding.credential_ref.startswith("re_")
