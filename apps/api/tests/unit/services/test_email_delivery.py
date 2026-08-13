"""Guards for the mail path that had never delivered a message.

On 2026-08-13 prod could not send any email, four independent ways at once:
the transport spoke SMTP into a namespace that only permits 443; the
magic-link sender did not exist; verification mail was scheduled as an
unbound instance method; and half the templates extended a path the loader
could not resolve, so the body silently degraded to a one-line fallback.

Every fault was invisible to the request path — the API returned 200 and the
UI said "check your inbox" — so these tests assert the things a 200 cannot.
"""

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from app.services import email_service as email_module
from app.services.email_service import EmailService


class TestSendersExist:
    """The magic-link route called a method that was never defined."""

    def test_magic_link_sender_exists(self):
        assert hasattr(EmailService, "send_magic_link_email")

    @pytest.mark.parametrize(
        "task_name",
        ["send_magic_link_email_task", "send_password_reset_email_task",
         "send_verification_email_task"],
    )
    def test_background_entrypoints_are_module_level(self, task_name):
        """Routers must schedule module-level coroutines.

        `background_tasks.add_task(EmailService.send_x, email, token)` calls an
        instance method unbound, binding `email` to `self` — it dies on the
        first attribute access. Module-level functions cannot be misused
        that way.
        """
        task = getattr(email_module, task_name)
        assert inspect.iscoroutinefunction(task)
        assert "self" not in inspect.signature(task).parameters

    def test_routers_do_not_schedule_unbound_methods(self):
        """Regression for the call convention itself."""
        source = inspect.getsource(inspect.getmodule(EmailService))
        from app.routers.v1 import auth

        auth_source = inspect.getsource(auth)
        assert "EmailService.send_verification_email," not in auth_source
        assert "EmailService.send_magic_link_email," not in auth_source
        assert source  # module imported cleanly


class TestTransport:
    """SMTP is unreachable from the cluster; 443 is not."""

    @pytest.mark.asyncio
    async def test_resend_provider_uses_https_api_not_smtp(self):
        service = EmailService()
        with patch.object(
            service, "_send_via_resend", new=AsyncMock(return_value=True)
        ) as resend, patch("smtplib.SMTP") as smtp:
            with patch.object(email_module.settings, "EMAIL_PROVIDER", "resend"), patch.object(
                email_module.settings, "RESEND_API_KEY", "re_test_key"
            ):
                sent = await service._send_email("a@b.test", "subject", "<p>hi</p>", "hi")
        assert sent is True
        resend.assert_awaited_once()
        smtp.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_transport_reports_failure_rather_than_success(self):
        """This returned True before, making an undeliverable mail look sent."""
        service = EmailService()
        with patch.object(email_module.settings, "EMAIL_PROVIDER", "smtp"), patch.object(
            email_module.settings, "SMTP_HOST", None
        ):
            sent = await service._send_email("a@b.test", "subject", "<p>hi</p>", "hi")
        assert sent is False


class TestTemplatesRender:
    """The loader is rooted at templates/email, so `email/base.html` is wrong."""

    @pytest.mark.parametrize(
        "template",
        ["password_reset.html", "verification.html", "welcome.html", "magic_link.html",
         "security_alert.html", "mfa_recovery.html"],
    )
    # Name kept short on purpose: a longer snake_case name here matched
    # TruffleHog's Lob API-key pattern and failed secret scanning (2026-08-13).
    def test_template_resolves_base(self, template):
        service = EmailService()
        rendered = service.jinja_env.get_template(template).render(
            user_name="x", current_year=2026, subject="s"
        )
        assert "<html" in rendered.lower()

    @pytest.mark.parametrize(
        ("template", "link_var"),
        [
            ("password_reset.html", "reset_link"),
            ("verification.html", "verification_link"),
            ("magic_link.html", "magic_link"),
        ],
    )
    def test_action_button_carries_a_real_href(self, template, link_var):
        """Templates referenced *_link while the service passed only *_url,
        so every button rendered with an empty href."""
        service = EmailService()
        rendered = service.jinja_env.get_template(template).render(
            **{link_var: "https://example.test/go?token=abc"},
            user_name="x",
            current_year=2026,
            subject="s",
        )
        assert 'href=""' not in rendered
        assert "https://example.test/go?token=abc" in rendered

    def test_render_helper_injects_shared_context(self):
        service = EmailService()
        rendered = service._render_template("magic_link.html", {"magic_link": "https://x.test/a"})
        assert "https://x.test/a" in rendered
        # base.html footer needs current_year; absent, Jinja renders "" silently.
        assert str(__import__("datetime").datetime.utcnow().year) in rendered


class TestMagicLinkCallbackRoute:
    """A clicked link is a GET; /magic-link/verify is a POST returning JSON."""

    def test_get_callback_route_is_registered(self):
        from app.routers.v1.auth import router

        get_paths = {
            route.path
            for route in router.routes
            if "GET" in getattr(route, "methods", set())
        }
        assert any(path.endswith("/magic-link/callback") for path in get_paths), get_paths
