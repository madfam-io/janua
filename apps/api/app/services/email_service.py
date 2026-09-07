"""
Email service for sending verification, password reset, and notification emails
"""

import hashlib
import json
import secrets
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import httpx
import redis.asyncio as redis
import structlog

from app.config import settings
from app.services.email_branding import (
    default_formality_for,
    resolve_branding,
    timezone_for,
)
from app.services.email_i18n import (
    FALLBACK_LOCALE,
    FORMALITY_TU,
    FORMALITY_USTED,
    build_email_environment,
    now_for_timezone,
    resolve_formality,
    resolve_formality_for_request,
    resolve_locale,
    stamp_subject,
    subject_for,
    template_candidates,
)

logger = structlog.get_logger()


def _redact_email(email: str) -> str:
    """Redact email address for logging (shows first 2 chars and domain)."""
    if not email or "@" not in email:
        return "[redacted]"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***@{domain}"


def resolve_sender(redirect_url: str | None = None) -> tuple[str, str]:
    """The (display name, address) every message comes FROM.

    ALWAYS `MADFAM <hola@madfam.io>`. Deliberately not per-tenant, and not
    per-platform. The address is the one a client can simply reply to, which
    is also why it is the `support` link in the footer; `config.py` defaults
    EMAIL_FROM_ADDRESS to it.

    WHY IT USED TO BE `Janua <noreply@janua.dev>` AND WHY THAT WAS WRONG. The
    first message a fractional-CTO client ever receives is a sign-in link. It
    arrived from a brand they had never heard of, on a domain unrelated to
    anything they had been told about, asking them to authenticate — which is
    indistinguishable from phishing, and deleting it is the correct reaction
    from a careful person.

    WHY NOT THE CLIENT'S OWN NAME EITHER. An earlier version of this function
    put the tenant on the From line (`Crea Tu Mundo <hola@madfam.io>`).
    That optimises the wrong thing. Bespoke clients meet several MADFAM
    platforms over an engagement — Janua for identity, Nauta for the
    workspace, Karafiel for documents — and a sender that changes per tenant
    or per product teaches them nothing and looks like several vendors. One
    consistent sender is what builds recognition, and recognition is what
    makes the NEXT email safe to open. The platform is credited inside the
    message, "Powered by", where it informs without competing.

    WHY ONE DOMAIN, NOT `noreply@<tenant>.madfam.io`. Per-subdomain sending
    splits reputation across domains that each send a handful of messages a
    year, and a domain with no reputation lands in spam. One verified domain
    accumulates reputation across every client and every service, with one
    SPF/DKIM/DMARC setup instead of N. madfam.io is Resend-verified.

    THIS IS PHASE 1 OF A TWO-PHASE POLICY, not a permanent answer. See
    `docs/EMAIL_SENDER_POLICY.md`.

      Phase 1 (now, and every new engagement): MADFAM sends, MADFAM brands,
      the platform is credited. The client is meeting our ecosystem for the
      first time and we control the sending domain, so this is the only shape
      that is both recognisable and deliverable.

      Phase 2 (once MADFAM manages the client's own domain, e.g.
      creatumundo.mx): mail comes from THEIR domain with THEIR branding. It
      requires their domain verified in Resend — their DNS, which is exactly
      what "we manage their web presence" gives us.

    `redirect_url` is accepted and unused ON PURPOSE. It is the Phase 2 hook:
    the redirect host identifies the tenant, so when a client's domain is
    verified this function can switch senders without another signature change
    through four callers. DO NOT REMOVE IT because it is currently unused —
    that is the seam, not dead code.
    """
    del redirect_url  # Phase 2 hook; see docstring before deleting
    name = settings.FROM_NAME or settings.EMAIL_FROM_NAME or "MADFAM"
    address = settings.FROM_EMAIL or settings.EMAIL_FROM_ADDRESS
    return name, address


class EmailService:
    """Email service for sending transactional emails"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.template_dir = Path(__file__).parent.parent / "templates" / "email"
        # Shared factory: base.html's localized chrome sits outside every
        # content block, so the globals backing it must exist on every
        # environment that loads this directory.
        self.jinja_env = build_email_environment(self.template_dir)

    async def send_verification_email(
        self,
        email: str,
        user_name: str = None,
        user_id: str = None,
        locale: Optional[str] = None,
        formality: Optional[str] = None,
        user: Any = None,
    ) -> str:
        """Send email verification email and return verification token"""

        recipient_locale = resolve_locale(locale, user=user, default=self._default_locale())
        recipient_formality = resolve_formality(formality, user=user)

        # Generate verification token
        verification_token = self._generate_verification_token()

        # Store token in Redis with 24-hour expiry.
        # Audit 2026-04-23 M2: use JSON rather than `str(dict)` so the read
        # path never needs `ast.literal_eval` on untrusted data.
        if self.redis_client:
            token_key = f"email_verification:{verification_token}"
            token_data = {
                "email": email,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "type": "email_verification",
            }
            await self.redis_client.setex(
                token_key, 24 * 60 * 60, json.dumps(token_data)
            )  # 24 hours

        # Generate verification URL. This must point at the dashboard app
        # (FRONTEND_URL, app.janua.dev), which serves /auth/verify-email —
        # not BASE_URL (janua.dev), the marketing site, which has no such
        # route and 404s.
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"

        # Prepare email content
        template_data = {
            "user_name": user_name or email.split("@")[0],
            "verification_url": verification_url,
            "verification_link": verification_url,
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }

        # Render email template. Stamped: verification is re-sendable ("resend
        # the code") and threads exactly like the magic link. No host signal
        # reaches this flow — it takes no redirect — so `timezone_for()` yields
        # the MADFAM default, CDMX.
        subject = stamp_subject(
            subject_for("verification", recipient_locale, recipient_formality),
            now_for_timezone(timezone_for()),
        )
        html_content = self._render_template(
            "verification.html", template_data, recipient_locale, recipient_formality
        )
        text_content = self._render_template(
            "verification.txt", template_data, recipient_locale, recipient_formality
        )

        # Send email
        success = await self._send_email(
            to_email=email, subject=subject, html_content=html_content, text_content=text_content
        )

        if success:
            logger.info("Verification email sent", email=_redact_email(email))
            return verification_token
        else:
            logger.error("Failed to send verification email", email=_redact_email(email))
            raise Exception("Failed to send verification email")

    async def verify_email_token(self, token: str) -> Dict[str, Any]:
        """Verify email verification token and return user data"""

        if not self.redis_client:
            raise Exception("Redis not available for token verification")

        token_key = f"email_verification:{token}"

        try:
            token_data = await self.redis_client.get(token_key)
            if not token_data:
                raise Exception("Invalid or expired verification token")

            # Audit 2026-04-23 M2: parse as JSON (was `ast.literal_eval`).
            # Fall back to the legacy `str(dict)` shape once so in-flight
            # tokens written before this deploy still verify — the fallback
            # can be removed after the 24h max-TTL soak.
            decoded = token_data.decode()
            try:
                token_info = json.loads(decoded)
            except ValueError:
                import ast  # noqa: PLC0415 — deprecated legacy path

                logger.warning(
                    "Legacy repr-format email token seen; remove this fallback "
                    "after a full 24h TTL soak past the M2 deploy."
                )
                token_info = ast.literal_eval(decoded)
            if not isinstance(token_info, dict):
                raise Exception("Malformed verification token payload")

            # Delete token after successful verification
            await self.redis_client.delete(token_key)

            logger.info("Email verified successfully", email=_redact_email(token_info["email"]))
            return token_info

        except Exception as e:
            logger.error("Token verification failed", error_type=type(e).__name__)
            raise Exception("Invalid or expired verification token")

    async def send_password_reset_email(
        self,
        email: str,
        reset_token: str,
        user_name: str = None,
        redirect_base: str = None,
        locale: Optional[str] = None,
        formality: Optional[str] = None,
        user: Any = None,
    ) -> str:
        """Send password reset email for an already-issued token.

        The token MUST be the caller's (stored in password_resets — the only
        store /password/reset validates against). This method previously
        generated its own token here, so the emailed link could never match
        the stored one.
        """

        recipient_locale = resolve_locale(locale, user=user, default=self._default_locale())
        # Same requester-voice chain as the magic link: this flow also carries a
        # product host (`redirect_base`), so the product's own register is the
        # tier below the reader's stored choice rather than a global `usted`.
        recipient_formality = resolve_formality_for_request(
            formality,
            user=user,
            client_default=default_formality_for(redirect_url=redirect_base),
        )

        # Mirror to Redis for observability (audit 2026-04-23 M2: JSON).
        if self.redis_client:
            token_key = f"password_reset:{reset_token}"
            token_data = {
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "type": "password_reset",
            }
            await self.redis_client.setex(token_key, 60 * 60, json.dumps(token_data))  # 1 hour

        # Generate reset URL. redirect_base is a caller-validated product page
        # (see PASSWORD_RESET_REDIRECT_ORIGINS); the default is the API's own
        # hosted reset page (2026-08-13) — the FRONTEND_URL default before it
        # pointed at an auth-walled route (app.janua.dev/auth/reset-password
        # redirects to /login), so the default recovery path could never
        # complete: the one user guaranteed unable to log in is the one
        # holding a reset token.
        if redirect_base:
            reset_url = f"{redirect_base}?token={reset_token}"
        else:
            reset_url = f"{settings.BASE_URL}/api/v1/auth/reset-password?token={reset_token}"

        # Prepare email content
        template_data = {
            "user_name": user_name or email.split("@")[0],
            "reset_url": reset_url,
            "reset_link": reset_url,
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }

        # Render email template. Stamped like the magic link, and for the same
        # reason: a reset is re-requested when the first one seems not to have
        # arrived, so a constant subject threads the live link under the dead
        # ones. `redirect_base` is this flow's host signal (the product page
        # that consumes the token), so the stamp is in that product's zone.
        subject = stamp_subject(
            subject_for("password_reset", recipient_locale, recipient_formality),
            now_for_timezone(timezone_for(redirect_url=redirect_base)),
        )
        html_content = self._render_template(
            "password_reset.html", template_data, recipient_locale, recipient_formality
        )
        text_content = self._render_template(
            "password_reset.txt", template_data, recipient_locale, recipient_formality
        )

        # Send email
        success = await self._send_email(
            to_email=email, subject=subject, html_content=html_content, text_content=text_content
        )

        if success:
            logger.info("Password reset email sent", email=_redact_email(email))
            return reset_token
        else:
            logger.error("Failed to send password reset email", email=_redact_email(email))
            raise Exception("Failed to send password reset email")

    async def send_welcome_email(
        self,
        email: str,
        user_name: str = None,
        locale: Optional[str] = None,
        formality: Optional[str] = None,
        user: Any = None,
    ) -> bool:
        """Send welcome email to new user"""

        recipient_locale = resolve_locale(locale, user=user, default=self._default_locale())
        recipient_formality = resolve_formality(formality, user=user)

        template_data = {
            "user_name": user_name or email.split("@")[0],
            "dashboard_url": f"{settings.BASE_URL}/dashboard",
            "dashboard_link": f"{settings.BASE_URL}/dashboard",
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }

        # Render email template
        subject = subject_for("welcome", recipient_locale, recipient_formality)
        html_content = self._render_template(
            "welcome.html", template_data, recipient_locale, recipient_formality
        )
        text_content = self._render_template(
            "welcome.txt", template_data, recipient_locale, recipient_formality
        )

        # Send email
        success = await self._send_email(
            to_email=email, subject=subject, html_content=html_content, text_content=text_content
        )

        if success:
            logger.info("Welcome email sent", email=_redact_email(email))
        else:
            logger.error("Failed to send welcome email", email=_redact_email(email))

        return success

    def _generate_verification_token(self) -> str:
        """Generate a secure verification token"""
        # Generate 32-byte random token
        random_bytes = secrets.token_bytes(32)
        # Create deterministic hash for consistent length
        token_hash = hashlib.sha256(random_bytes).hexdigest()
        return token_hash[:64]  # 64-char hex string

    def _render_template(
        self,
        template_name: str,
        data: Dict[str, Any],
        locale: Optional[str] = None,
        formality: Optional[str] = None,
    ) -> str:
        """Render email template with data, in the recipient's language.

        Injects the context every template inherits from base.html. Jinja
        renders an undefined variable as empty string, so a missing value here
        does not fail loudly — it silently ships a mail with a blank footer or,
        worse, a blank button href. Callers supply the `*_link` names the
        templates actually reference.

        `template_name` is always the English name; the localized file is
        selected here. `select_template` walks the candidates in order and
        takes the first that exists, so a language with no translation for
        this particular message still sends — in English — rather than
        raising into the fallback text below.

        `formality` is the Spanish register (`tu` / `usted`). It goes into the
        context rather than into the template name, so it costs zero extra
        template files: `t()` resolves each key against it. An absent or
        unrecognized value renders `usted`.
        """
        resolved_locale = resolve_locale(locale, default=self._default_locale())
        resolved_formality = resolve_formality(formality)
        try:
            template = self.jinja_env.select_template(
                template_candidates(template_name, resolved_locale)
            )
            # Chrome follows the template that actually won, not the language
            # that was asked for. When a message has no translation yet, the
            # English body is selected — and an English body inside a Spanish
            # header and footer is a worse email than a consistently English
            # one. Keeps "body language == frame language" always true.
            body_locale = (
                resolved_locale
                if (template.name or "").startswith(f"{resolved_locale}/")
                else FALLBACK_LOCALE
            )
            context = {
                "current_year": datetime.utcnow().year,
                # The frame is MADFAM's, so the fallback subject is too.
                "subject": data.get("subject", "MADFAM"),
                "locale": body_locale,
                # madfam.io serves its legal pages under a LOCALE PREFIX, and
                # only `en` and `es` exist. Derived from the language the body
                # actually rendered in — `body_locale`, not the requested one —
                # so an untranslated body that fell back to English does not
                # link a Spanish reader to a page in the wrong language.
                # Anything unknown falls to `en`, which exists, rather than
                # producing a 404 that asserts a notice we then do not show.
                "legal_locale": "es" if str(body_locale).lower().startswith("es") else "en",
                # `t()` reads this off the context, which is why base.html and
                # every es/ template pick up the register without naming it.
                "formality": resolved_formality,
                **data,
            }
            return template.render(**context)
        except Exception as e:
            logger.error(
                "Template rendering failed",
                template=template_name,
                locale=resolved_locale,
                error_type=type(e).__name__,
            )
            return self._fallback_body(template_name, data, resolved_locale, resolved_formality)

    @staticmethod
    def _default_locale() -> Optional[str]:
        """The deployment-wide default, read at call time so tests and
        per-environment overrides of DEFAULT_EMAIL_LOCALE take effect."""
        return getattr(settings, "DEFAULT_EMAIL_LOCALE", None)

    @staticmethod
    def _fallback_body(
        template_name: str,
        data: Dict[str, Any],
        locale: str,
        formality: str = FORMALITY_USTED,
    ) -> str:
        """Last-resort plain text when the template itself failed to render.

        Localized too: a recipient hitting the degraded path is no more
        likely to read English than one hitting the happy path — and no more
        likely to have changed their mind about being addressed as `tú`. The
        degraded path is still an email someone reads.
        """
        spanish = locale == "es"
        informal = spanish and formality == FORMALITY_TU
        if "verification" in template_name:
            url = data.get("verification_url", "")
            if informal:
                return f"Verifica tu correo electrónico aquí: {url}"
            return (
                f"Verifique su correo electrónico aquí: {url}"
                if spanish
                else f"Please verify your email by clicking: {url}"
            )
        if "magic_link" in template_name:
            url = data.get("magic_url", "")
            if informal:
                return f"Inicia sesión en tu portal aquí: {url}"
            return (
                f"Inicie sesión en su portal aquí: {url}"
                if spanish
                else f"Sign in to your portal by clicking: {url}"
            )
        if "password_reset" in template_name:
            url = data.get("reset_url", "")
            if informal:
                return f"Restablece tu contraseña aquí: {url}"
            return (
                f"Restablezca su contraseña aquí: {url}"
                if spanish
                else f"Reset your password by clicking: {url}"
            )
        if "welcome" in template_name:
            name = data.get("user_name", "there")
            if informal:
                return f"Te damos la bienvenida a Janua, {name}."
            return (
                f"Le damos la bienvenida a Janua, {name}."
                if spanish
                else f"Welcome to Janua, {name}!"
            )
        if "invitation" in template_name:
            url = data.get("invitation_url", "")
            if informal:
                return f"Te han invitado a unirte a Janua: {url}"
            return (
                f"Le han invitado a unirse a Janua: {url}"
                if spanish
                else f"You've been invited to join Janua: {url}"
            )
        # Register-neutral: names a state, does not address the reader.
        return "Contenido no disponible" if spanish else "Email content unavailable"

    async def send_magic_link_email(
        self,
        email: str,
        magic_token: str,
        redirect_url: Optional[str] = None,
        locale: Optional[str] = None,
        formality: Optional[str] = None,
        user: Any = None,
    ) -> bool:
        """Send a passwordless sign-in link.

        When the request named a redirect_url (allowlist-validated at request
        time), the emailed link lives on THAT host: the recipient clicks a URL
        on the product's own domain and the product exchanges the one-time
        token via POST /api/v1/auth/magic-link/verify. A first-contact email
        whose link points at api.janua.dev reads as phishing next to the
        product the client was just told to trust; the sender, the link, and
        the destination must all agree.

        Without a redirect_url the link falls back to Janua's own GET callback
        — a clicked link is a GET, and only Janua can trade the token then.

        The REGISTER follows the requester. `formality` is what the requesting
        product asked for and wins outright; below it sit the reader's own
        stored choice and then the product's default voice, read off the same
        redirect host that already picks the branding. That last tier is the
        one that matters in practice — almost every user row is NULL — and it
        is why a crea-map link now reads «Inicia sesión en tu portal» while a
        nauta-portal link still reads «Inicie sesión en su portal».
        """
        recipient_locale = resolve_locale(locale, user=user, default=self._default_locale())
        recipient_formality = resolve_formality_for_request(
            formality,
            user=user,
            client_default=default_formality_for(redirect_url=redirect_url),
        )
        if redirect_url:
            separator = "&" if "?" in redirect_url else "?"
            magic_url = f"{redirect_url}{separator}token={magic_token}"
        else:
            # PUBLIC domain, never the api.janua.dev default. This fallback fires
            # when the request named no redirect_url (a clicked link is a GET, and
            # only Janua can trade the token then). `public_base_url` prefers
            # JANUA_CUSTOM_DOMAIN (e.g. auth.madfam.io) — so a first-contact auth
            # email never carries a dev domain. (Before: `API_BASE_URL or
            # BASE_URL` emitted api.janua.dev because API_BASE_URL's default is
            # truthy and short-circuited the correctly-set BASE_URL.)
            callback = f"{settings.public_base_url}/api/v1/auth/magic-link/callback"
            magic_url = f"{callback}?token={magic_token}"

        template_data = {
            "user_name": email.split("@")[0],
            "magic_url": magic_url,
            "magic_link": magic_url,
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
            # BODY branding (header wordmark + palette, footer credit) resolved
            # from the redirect host — the tenant the link sends the person back
            # TO. Defaults to MADFAM, so an unknown or absent host renders
            # exactly today's frame. The From line is unaffected: `resolve_sender`
            # below still returns MADFAM. See app/services/email_branding.py.
            **resolve_branding(redirect_url=redirect_url),
        }

        # Stamped with the SEND MOMENT in the requester's operating timezone.
        # Without it every request in a thread carries the same subject and the
        # reader opens the oldest, expired link; with it "the newest one" is
        # readable rather than guessable. The zone comes off the same host
        # signal as the branding and the voice — see email_branding.timezone_for
        # — and the clock is read here, per send, never cached at import.
        subject = stamp_subject(
            subject_for("magic_link", recipient_locale, recipient_formality),
            now_for_timezone(timezone_for(redirect_url=redirect_url)),
        )
        html_content = self._render_template(
            "magic_link.html", template_data, recipient_locale, recipient_formality
        )
        text_content = self._render_template(
            "magic_link.txt", template_data, recipient_locale, recipient_formality
        )

        # `redirect_url` travels through so the From line can carry the CLIENT'S
        # name. This is the one flow where it matters most: a magic link is the
        # first message a new client ever receives, and it asks them to
        # authenticate. `resolve_sender` reads the tenant off this host — the
        # same host the link sends them back to — so the sender and the
        # destination agree, which is what makes it read as legitimate rather
        # than as phishing.
        sent = await self._send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            redirect_url=redirect_url,
        )
        if sent:
            logger.info("Magic link email sent", email=_redact_email(email))
        else:
            logger.error("Failed to send magic link email", email=_redact_email(email))
        return sent

    async def send_invitation_email(
        self,
        email: str,
        invite_url: str,
        organization_name: str,
        inviter_name: str,
        role: str = "member",
        expires_at: Optional[datetime] = None,
        teams: Optional[list] = None,
    ) -> bool:
        """Send an organization invitation.

        The invitation templates have existed since the templates directory
        did, but nothing on a live path ever rendered them — the invitation
        service hand-rolled its own HTML string and handed it to a method that
        does not exist on this class. This is the missing seam: one place that
        renders the maintained templates and puts them on the same transport
        as every other transactional message.
        """
        template_data = {
            "inviter_name": inviter_name,
            "organization_name": organization_name,
            "role": role,
            # The template renders href="{{ invitation_url }}"; `invitation_link`
            # mirrors the `*_link` naming the other templates use so a future
            # rename of either name still finds a value rather than a blank href.
            "invitation_url": invite_url,
            "invitation_link": invite_url,
            "expires_at": (expires_at.strftime("%B %d, %Y at %I:%M %p UTC") if expires_at else ""),
            "teams": teams or [],
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }

        subject = f"{inviter_name} invited you to join {organization_name} on Janua"
        html_content = self._render_template("invitation.html", template_data)
        text_content = self._render_template("invitation.txt", template_data)

        sent = await self._send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
        if sent:
            logger.info("Invitation email sent", email=_redact_email(email))
        else:
            logger.error("Failed to send invitation email", email=_redact_email(email))
        return sent

    async def _send_via_resend(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None,
        redirect_url: str | None = None,
    ) -> bool:
        """Send through Resend's HTTPS API.

        This exists because SMTP is not reachable from this cluster at all:
        the namespace runs default-deny egress and permits 443 only, so every
        SMTP attempt died with ConnectionRefusedError on 587 AND 465 (verified
        from the pod, 2026-08-13). EMAIL_PROVIDER has said "resend" and
        RESEND_API_KEY has been present the whole time — only the transport
        disagreed. Nothing this service ever sent left the cluster.
        """
        payload: Dict[str, Any] = {
            "from": formataddr(resolve_sender(redirect_url)),
            "to": [to_email],
            "subject": subject,
        }
        if html_content:
            payload["html"] = html_content
        if text_content:
            payload["text"] = text_content

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json=payload,
            )

        if response.status_code >= 400:
            # Body may name a misconfiguration (unverified domain, bad key);
            # it carries no recipient content, so it is safe to log.
            logger.error(
                "Resend rejected the message",
                to=_redact_email(to_email),
                status_code=response.status_code,
                detail=response.text[:300],
            )
            return False
        return True

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None,
        redirect_url: str | None = None,
    ) -> bool:
        """Send an email via the configured provider.

        `redirect_url` is optional and defaults to None, so every existing
        caller keeps the generic MADFAM sender. Only the flows that know which
        tenant they are addressing — the magic link knows, because it already
        carries where it is sending the person back TO — pass it and get the
        client's own name on the From line.
        """

        try:
            if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
                return await self._send_via_resend(
                    to_email, subject, html_content, text_content, redirect_url
                )

            # Check if email configuration is available
            if not hasattr(settings, "SMTP_HOST") or not settings.SMTP_HOST:
                # No transport at all. This used to return True, which made an
                # undeliverable email indistinguishable from a sent one for
                # every caller — return False so callers can say so honestly.
                logger.error(
                    "No email transport configured — message NOT sent",
                    to=_redact_email(to_email),
                    provider=settings.EMAIL_PROVIDER,
                )
                return False

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr(resolve_sender(redirect_url))
            msg["To"] = to_email

            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                msg.attach(text_part)

            if html_content:
                html_part = MIMEText(html_content, "html", "utf-8")
                msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

                text = msg.as_string()
                server.sendmail(settings.FROM_EMAIL, [to_email], text)

            return True

        except Exception as e:
            logger.error(
                "Failed to send email", to=_redact_email(to_email), error_type=type(e).__name__
            )
            return False


# Create email service instance
def get_email_service(redis_client: Optional[redis.Redis] = None) -> EmailService:
    """Get email service instance"""
    return EmailService(redis_client)


async def send_password_reset_email_task(
    email: str,
    reset_token: str,
    redirect_base: Optional[str] = None,
    locale: Optional[str] = None,
    formality: Optional[str] = None,
) -> None:
    """Background-task entrypoint for the forgot-password flow.

    Instantiates the real mailer per-call (BackgroundTasks gives no DI) and
    never raises — a mail failure must not surface into the request path.
    Without SMTP_HOST configured, _send_email already degrades to a logged
    no-op; the warning below makes that state visible instead of silent.

    `locale` is read off the User row by the router: a background task has no
    DB session of its own, so the recipient's stored language has to be
    resolved while the request still holds one.
    """
    try:
        service = EmailService()
        sent = await service.send_password_reset_email(
            email,
            reset_token,
            redirect_base=redirect_base,
            locale=locale,
            formality=formality,
        )
        if not sent:
            logger.warning(
                "Password reset email NOT sent (mailer unconfigured or send failed) — "
                "the user will never receive the link"
            )
    except Exception:
        logger.exception("Password reset email task failed")


async def send_magic_link_email_task(
    email: str,
    magic_token: str,
    redirect_url: Optional[str] = None,
    locale: Optional[str] = None,
    formality: Optional[str] = None,
    user_formality: Optional[str] = None,
) -> None:
    """Background-task entrypoint for the magic-link flow.

    Routers must schedule THIS, not `EmailService.send_magic_link_email`:
    these are instance methods, so scheduling the unbound attribute binds the
    first argument to `self` and the call dies on the first attribute access.
    That is exactly how the magic-link route failed — it referenced a method
    that did not exist at all, raising AttributeError before any mail was
    attempted, which is why no client could ever sign in passwordlessly.

    TWO REGISTER ARGUMENTS, DELIBERATELY. `formality` is what the REQUESTING
    PRODUCT asked for; `user_formality` is what the RECIPIENT chose, read off
    the User row by the router because a background task holds no DB session
    (the same reason `locale` is passed rather than looked up). They are
    separate parameters because they sit at different precedence tiers and
    collapsing them would let a product's default silently overwrite a
    person's stated preference. `user_formality` is wrapped back into the
    duck-typed `user` shape the resolver reads, rather than widening the
    resolver to take loose scalars.
    """
    try:
        service = EmailService()
        sent = await service.send_magic_link_email(
            email,
            magic_token,
            redirect_url,
            locale=locale,
            formality=formality,
            user=SimpleNamespace(spanish_formality=user_formality) if user_formality else None,
        )
        if not sent:
            logger.warning(
                "Magic link email NOT sent — the recipient will never receive a sign-in link",
                email=_redact_email(email),
            )
    except Exception:
        logger.exception("Magic link email task failed")


async def send_verification_email_task(
    email: str,
    verification_token: str,
    user_name: Optional[str] = None,
    locale: Optional[str] = None,
    formality: Optional[str] = None,
) -> None:
    """Background-task entrypoint for email verification.

    Takes the CALLER's token deliberately. `EmailService.send_verification_email`
    mints its own token into Redis, but `/auth/verify-email` validates against
    the `email_verifications` table — so the token that got mailed and the token
    that could be verified were never the same value.
    """
    try:
        service = EmailService()
        recipient_locale = resolve_locale(locale, default=service._default_locale())
        recipient_formality = resolve_formality(formality)
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
        template_data = {
            "user_name": user_name or email.split("@")[0],
            "verification_url": verification_url,
            # verification.html renders the button as href="{{ verification_link }}".
            # This path passed only *_url, so the one email every new account
            # receives shipped with an empty href.
            "verification_link": verification_url,
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }
        sent = await service._send_email(
            to_email=email,
            # Stamped like the method above — this task renders the same
            # message on the same pipeline and must not diverge from it.
            subject=stamp_subject(
                subject_for("verification", recipient_locale, recipient_formality),
                now_for_timezone(timezone_for()),
            ),
            html_content=service._render_template(
                "verification.html", template_data, recipient_locale, recipient_formality
            ),
            text_content=service._render_template(
                "verification.txt", template_data, recipient_locale, recipient_formality
            ),
        )
        if not sent:
            logger.warning("Verification email NOT sent", email=_redact_email(email))
    except Exception:
        logger.exception("Verification email task failed")
