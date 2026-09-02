"""The emailed magic link lands on the PRODUCT, not on api.janua.dev.

Found live 2026-08-15, mid client-ceremony rehearsal: the first email a new
client receives asked them to click an api.janua.dev URL — a host they have
never been told about — and, because the rehearsal host was missing from the
allowlist, the click signed them in at Janua and dead-ended on a recovery
page. Two rules fell out of that afternoon:

1. When the request names a redirect_url, the link in the email is built ON
   that host (`https://<product-host>/portal/verify?token=...`); the product
   exchanges the one-time token via POST /api/v1/auth/magic-link/verify.
2. A supplied-but-disallowed redirect_url fails the REQUEST with a 400. The
   old behaviour nulled it silently and mailed a link that could only ever
   dead-end — a failure neither the product nor the recipient could see
   coming.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_link_is_built_on_the_redirect_host():
    service = EmailService()
    with patch.object(service, "_send_email", new=AsyncMock(return_value=True)) as send:
        await service.send_magic_link_email(
            "cliente@example.test",
            "one-time-token",
            redirect_url="https://ensayo.madfam.io/portal/verify",
        )
    html = send.await_args.kwargs["html_content"]
    text = send.await_args.kwargs["text_content"]
    assert "https://ensayo.madfam.io/portal/verify?token=one-time-token" in html
    assert "https://ensayo.madfam.io/portal/verify?token=one-time-token" in text
    assert "magic-link/callback" not in html


@pytest.mark.asyncio
async def test_redirect_host_with_existing_query_appends_with_ampersand():
    service = EmailService()
    with patch.object(service, "_send_email", new=AsyncMock(return_value=True)) as send:
        await service.send_magic_link_email(
            "cliente@example.test",
            "tok",
            redirect_url="https://ensayo.madfam.io/portal/verify?next=%2Ffacturas",
        )
    # HTML entity-escapes the ampersand; the plain-text body carries it raw.
    html = send.await_args.kwargs["html_content"]
    text = send.await_args.kwargs["text_content"]
    assert "https://ensayo.madfam.io/portal/verify?next=%2Ffacturas&amp;token=tok" in html
    assert "https://ensayo.madfam.io/portal/verify?next=%2Ffacturas&token=tok" in text


@pytest.mark.asyncio
async def test_no_redirect_still_falls_back_to_the_janua_callback():
    """Products that never send redirect_url keep the GET-callback contract:
    a clicked link is a GET and only Janua can trade the token then."""
    service = EmailService()
    with patch.object(service, "_send_email", new=AsyncMock(return_value=True)) as send:
        await service.send_magic_link_email("cliente@example.test", "tok")
    html = send.await_args.kwargs["html_content"]
    assert "/api/v1/auth/magic-link/callback?token=tok" in html
    # THE BUG THIS FILE EXISTS TO PREVENT: the fallback must never emit the
    # api.janua.dev DEV host. It used to (`API_BASE_URL or BASE_URL`, and
    # API_BASE_URL defaults to https://api.janua.dev, short-circuiting a
    # correctly-set BASE_URL) — a dev domain in a first-contact auth email.
    assert "api.janua.dev" not in html


@pytest.mark.asyncio
async def test_fallback_prefers_the_custom_domain(monkeypatch):
    """A white-label deployment (JANUA_CUSTOM_DOMAIN=auth.madfam.io) must emit
    the fallback callback on ITS domain, not api.janua.dev — even though
    API_BASE_URL still carries its dev-host default."""
    from app.services import email_service as es

    monkeypatch.setattr(es.settings, "JANUA_CUSTOM_DOMAIN", "auth.madfam.io", raising=False)
    service = EmailService()
    with patch.object(service, "_send_email", new=AsyncMock(return_value=True)) as send:
        await service.send_magic_link_email("cliente@example.test", "tok")
    html = send.await_args.kwargs["html_content"]
    assert "https://auth.madfam.io/api/v1/auth/magic-link/callback?token=tok" in html
    assert "api.janua.dev" not in html


def test_send_route_refuses_a_disallowed_destination_loudly():
    """The 400 must happen at request time. Silently nulling the redirect
    mails a link that signs the user in and then strands them — the exact
    rehearsal failure this file exists to prevent."""
    import inspect

    from app.routers.v1 import auth

    source = inspect.getsource(auth.send_magic_link)
    assert "raise HTTPException" in source.split("safe_redirect_url = validate_redirect_url")[1].split(
        "magic_token"
    )[0], "failed redirect validation must raise, not proceed"
    assert "we simply won't include a redirect" not in source
