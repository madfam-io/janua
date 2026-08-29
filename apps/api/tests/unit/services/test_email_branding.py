"""Per-tenant BODY branding, and the invariants that keep it Phase-1 safe.

Context: docs/EMAIL_SENDER_POLICY.md. Phase 1 keeps ONE sender —
`MADFAM <hola@madfam.io>` — for every message from every platform. This suite
pins a refinement of Phase 1: the BODY may carry a client tenant's name in the
header and credit MADFAM in the footer, while the From line does not move.

The load-bearing guarantees, each with a test that fails loudly if it breaks:

  * a CTM-context send still comes FROM MADFAM (the policy line)
  * a non-CTM / unknown / absent signal renders TODAY's MADFAM frame
  * the footer reads "Con tecnología de" (es) / "Powered by" (en), never
    "Impulsado por"
  * a CTM context puts "Crea Tu Mundo" in the header and MADFAM in the footer

Style follows tests/unit/services/test_email_delivery.py: render templates
directly and patch the transport with an AsyncMock rather than standing up a
live provider.
"""

from email.utils import formataddr
from unittest.mock import AsyncMock, patch

import pytest

from app.services import email_service as email_module
from app.services.email_branding import (
    CTM_ORG_ID,
    MADFAM_BRANDING,
    resolve_branding,
)
from app.services.email_service import EmailService, resolve_sender

CTM_REDIRECT = "https://crea-map.madfam.io/portal/verify?next=/"


# --------------------------------------------------------------------------
# The resolver
# --------------------------------------------------------------------------
class TestResolveBranding:
    def test_no_signal_is_madfam(self):
        assert resolve_branding() == MADFAM_BRANDING
        assert resolve_branding()["header_name"] == "MADFAM"
        assert resolve_branding()["platform_name"] == "Janua"

    def test_unknown_host_is_madfam(self):
        b = resolve_branding(redirect_url="https://example.test/go?token=abc")
        assert b["header_name"] == "MADFAM"

    def test_madfam_own_host_stays_madfam(self):
        """madfam.io is MADFAM's own host and must NOT resolve to a tenant."""
        b = resolve_branding(redirect_url="https://app.madfam.io/x")
        assert b["header_name"] == "MADFAM"

    @pytest.mark.parametrize(
        "url",
        [
            "https://crea-map.madfam.io/portal/verify",
            "https://ensayo-map.madfam.io/x",
            "https://kalya.app/verify?token=abc",
            "https://app.kalya.app/verify",  # subdomain of an allowed host
        ],
    )
    def test_ctm_hosts_resolve_to_ctm(self, url):
        b = resolve_branding(redirect_url=url)
        assert b["header_name"] == "Crea Tu Mundo"
        # Footer credits MADFAM (the platform underneath a client tenant).
        assert b["platform_name"] == "MADFAM"
        assert b["header_bg"] == "#1a2a8f"

    def test_lookalike_host_does_not_match(self):
        """Suffix match is on a dot boundary; `evilkalya.app` is not kalya."""
        b = resolve_branding(redirect_url="https://evilkalya.app/x")
        assert b["header_name"] == "MADFAM"

    def test_org_id_resolves_ctm(self):
        b = resolve_branding(org_id=CTM_ORG_ID)
        assert b["header_name"] == "Crea Tu Mundo"

    def test_org_id_takes_precedence_over_host(self):
        """A caller that knows the org id is authoritative over the host."""
        b = resolve_branding(
            redirect_url="https://example.test/go", org_id=CTM_ORG_ID
        )
        assert b["header_name"] == "Crea Tu Mundo"

    def test_resolver_never_returns_a_from_address(self):
        """Branding must not carry anything usable as a sender."""
        b = resolve_branding(redirect_url=CTM_REDIRECT)
        for key in b:
            assert "from" not in key.lower()
            assert "sender" not in key.lower()
            assert "email" not in key.lower()


# --------------------------------------------------------------------------
# The From line — the policy invariant
# --------------------------------------------------------------------------
class TestSenderNeverChanges:
    def test_resolve_sender_is_madfam_for_ctm_redirect(self):
        """resolve_sender ignores the redirect and returns MADFAM — always."""
        name, address = resolve_sender(CTM_REDIRECT)
        assert (name, address) == ("MADFAM", "hola@madfam.io")

    @pytest.mark.asyncio
    async def test_ctm_magic_link_still_sends_from_madfam(self):
        """A CTM-branded magic link comes FROM MADFAM, not from CTM.

        This is the policy line (EMAIL_SENDER_POLICY.md): BODY branding is
        per-tenant, the sender is not. We drive the real send path and read the
        From header off the Resend payload.
        """
        captured = {}

        async def fake_post(url, headers=None, json=None):
            captured["from"] = json["from"]

            class _Resp:
                status_code = 200
                text = ""

            return _Resp()

        service = EmailService()
        with patch.object(email_module.settings, "EMAIL_PROVIDER", "resend"), patch.object(
            email_module.settings, "RESEND_API_KEY", "re_test_key"
        ), patch("app.services.email_service.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(side_effect=fake_post)
            sent = await service.send_magic_link_email(
                "ana@creatumundo.mx",
                "tok123",
                redirect_url=CTM_REDIRECT,
                locale="es",
            )
        assert sent is True
        # From is MADFAM regardless of the CTM redirect.
        assert captured["from"] == formataddr(("MADFAM", "hola@madfam.io"))

    @pytest.mark.asyncio
    async def test_ctm_body_is_branded_but_from_is_not(self):
        """Same send: the HTML body carries CTM, the From carries MADFAM."""
        captured = {}

        async def fake_post(url, headers=None, json=None):
            captured.update(json)

            class _Resp:
                status_code = 200
                text = ""

            return _Resp()

        service = EmailService()
        with patch.object(email_module.settings, "EMAIL_PROVIDER", "resend"), patch.object(
            email_module.settings, "RESEND_API_KEY", "re_test_key"
        ), patch("app.services.email_service.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(side_effect=fake_post)
            await service.send_magic_link_email(
                "ana@creatumundo.mx", "tok123", redirect_url=CTM_REDIRECT, locale="es"
            )
        assert captured["from"] == formataddr(("MADFAM", "hola@madfam.io"))
        assert "Crea Tu Mundo" in captured["html"]
        assert "Con tecnología de" in captured["html"]
        assert "Impulsado por" not in captured["html"]


# --------------------------------------------------------------------------
# The rendered frame
# --------------------------------------------------------------------------
class TestRenderedFrame:
    def _render(self, locale=None, branding_url=None):
        service = EmailService()
        ctx = {"magic_link": "https://x.test/a"}
        if branding_url is not None:
            ctx.update(resolve_branding(redirect_url=branding_url))
        return service._render_template("magic_link.html", ctx, locale=locale)

    def test_default_render_is_madfam_frame(self):
        """No branding signal -> today's MADFAM header, byte-for-byte."""
        html = self._render(locale="en")
        assert (
            '<h1 style="margin: 0; font-size: 24px; font-weight: 600;">MADFAM</h1>'
            in html
        )
        assert "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)" in html
        assert "#1a2a8f" not in html
        # The MADFAM logo block is present for the MADFAM header.
        assert 'alt="MADFAM"' in html

    def test_default_es_footer_is_con_tecnologia_de_not_impulsado(self):
        html = self._render(locale="es")
        assert "Con tecnología de" in html
        assert "Impulsado por" not in html

    def test_ctm_header_reads_crea_tu_mundo(self):
        html = self._render(locale="es", branding_url=CTM_REDIRECT)
        assert "Crea Tu Mundo" in html
        assert "#1a2a8f" in html

    def test_ctm_header_drops_madfam_logo(self):
        """CTM header is typographic — no MADFAM logo in the header segment."""
        html = self._render(locale="es", branding_url=CTM_REDIRECT)
        header_seg = html.split('class="content"')[0]
        assert 'alt="MADFAM"' not in header_seg

    def test_ctm_es_footer_credits_madfam_with_con_tecnologia_de(self):
        html = self._render(locale="es", branding_url=CTM_REDIRECT)
        assert "Con tecnología de" in html
        assert "Impulsado por" not in html
        # The credited platform is MADFAM (madfam.io link in the footer).
        assert "madfam.io" in html

    def test_ctm_en_footer_says_powered_by(self):
        html = self._render(locale="en", branding_url=CTM_REDIRECT)
        assert "Powered by" in html
        assert "Impulsado" not in html
