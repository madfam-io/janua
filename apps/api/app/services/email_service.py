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
from typing import Any, Dict, Optional

import httpx
import redis.asyncio as redis
import structlog
from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = structlog.get_logger()


def _redact_email(email: str) -> str:
    """Redact email address for logging (shows first 2 chars and domain)."""
    if not email or "@" not in email:
        return "[redacted]"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***@{domain}"


class EmailService:
    """Email service for sending transactional emails"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir), autoescape=True)

    async def send_verification_email(
        self, email: str, user_name: str = None, user_id: str = None
    ) -> str:
        """Send email verification email and return verification token"""

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

        # Render email template
        subject = "Verify your Janua account"
        html_content = self._render_template("verification.html", template_data)
        text_content = self._render_template("verification.txt", template_data)

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
    ) -> str:
        """Send password reset email for an already-issued token.

        The token MUST be the caller's (stored in password_resets — the only
        store /password/reset validates against). This method previously
        generated its own token here, so the emailed link could never match
        the stored one.
        """

        # Mirror to Redis for observability (audit 2026-04-23 M2: JSON).
        if self.redis_client:
            token_key = f"password_reset:{reset_token}"
            token_data = {
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "type": "password_reset",
            }
            await self.redis_client.setex(
                token_key, 60 * 60, json.dumps(token_data)
            )  # 1 hour

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

        # Render email template
        subject = "Reset your Janua password"
        html_content = self._render_template("password_reset.html", template_data)
        text_content = self._render_template("password_reset.txt", template_data)

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

    async def send_welcome_email(self, email: str, user_name: str = None) -> bool:
        """Send welcome email to new user"""

        template_data = {
            "user_name": user_name or email.split("@")[0],
            "dashboard_url": f"{settings.BASE_URL}/dashboard",
            "dashboard_link": f"{settings.BASE_URL}/dashboard",
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }

        # Render email template
        subject = "Welcome to Janua!"
        html_content = self._render_template("welcome.html", template_data)
        text_content = self._render_template("welcome.txt", template_data)

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

    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render email template with data.

        Injects the context every template inherits from base.html. Jinja
        renders an undefined variable as empty string, so a missing value here
        does not fail loudly — it silently ships a mail with a blank footer or,
        worse, a blank button href. Callers supply the `*_link` names the
        templates actually reference.
        """
        try:
            template = self.jinja_env.get_template(template_name)
            context = {
                "current_year": datetime.utcnow().year,
                "subject": data.get("subject", "Janua"),
                **data,
            }
            return template.render(**context)
        except Exception as e:
            logger.error(
                "Template rendering failed", template=template_name, error_type=type(e).__name__
            )
            # Fallback to simple text
            if "verification" in template_name:
                return f"Please verify your email by clicking: {data.get('verification_url', '')}"
            elif "magic_link" in template_name:
                return f"Sign in to Janua by clicking: {data.get('magic_url', '')}"
            elif "password_reset" in template_name:
                return f"Reset your password by clicking: {data.get('reset_url', '')}"
            elif "welcome" in template_name:
                return f"Welcome to Janua, {data.get('user_name', 'there')}!"
            return "Email content unavailable"

    async def send_magic_link_email(
        self, email: str, magic_token: str, redirect_url: Optional[str] = None
    ) -> bool:
        """Send a passwordless sign-in link.

        The link points at Janua's own GET callback rather than at the product
        page: a clicked link is a GET, and only Janua can trade the one-time
        magic token for a session. The callback then forwards to redirect_url
        (already allowlist-validated when the link was requested).
        """
        callback = f"{settings.API_BASE_URL or settings.BASE_URL}/api/v1/auth/magic-link/callback"
        magic_url = f"{callback}?token={magic_token}"

        template_data = {
            "user_name": email.split("@")[0],
            "magic_url": magic_url,
            "magic_link": magic_url,
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }

        subject = "Your Janua sign-in link"
        html_content = self._render_template("magic_link.html", template_data)
        text_content = self._render_template("magic_link.txt", template_data)

        sent = await self._send_email(
            to_email=email, subject=subject, html_content=html_content, text_content=text_content
        )
        if sent:
            logger.info("Magic link email sent", email=_redact_email(email))
        else:
            logger.error("Failed to send magic link email", email=_redact_email(email))
        return sent

    async def _send_via_resend(
        self, to_email: str, subject: str, html_content: str, text_content: str = None
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
            "from": formataddr((settings.FROM_NAME or "Janua", settings.FROM_EMAIL)),
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
        self, to_email: str, subject: str, html_content: str, text_content: str = None
    ) -> bool:
        """Send an email via the configured provider."""

        try:
            if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
                return await self._send_via_resend(
                    to_email, subject, html_content, text_content
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
            msg["From"] = formataddr((settings.FROM_NAME or "Janua", settings.FROM_EMAIL))
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
    email: str, reset_token: str, redirect_base: Optional[str] = None
) -> None:
    """Background-task entrypoint for the forgot-password flow.

    Instantiates the real mailer per-call (BackgroundTasks gives no DI) and
    never raises — a mail failure must not surface into the request path.
    Without SMTP_HOST configured, _send_email already degrades to a logged
    no-op; the warning below makes that state visible instead of silent.
    """
    try:
        service = EmailService()
        sent = await service.send_password_reset_email(
            email, reset_token, redirect_base=redirect_base
        )
        if not sent:
            logger.warning(
                "Password reset email NOT sent (mailer unconfigured or send failed) — "
                "the user will never receive the link"
            )
    except Exception:
        logger.exception("Password reset email task failed")


async def send_magic_link_email_task(
    email: str, magic_token: str, redirect_url: Optional[str] = None
) -> None:
    """Background-task entrypoint for the magic-link flow.

    Routers must schedule THIS, not `EmailService.send_magic_link_email`:
    these are instance methods, so scheduling the unbound attribute binds the
    first argument to `self` and the call dies on the first attribute access.
    That is exactly how the magic-link route failed — it referenced a method
    that did not exist at all, raising AttributeError before any mail was
    attempted, which is why no client could ever sign in passwordlessly.
    """
    try:
        service = EmailService()
        sent = await service.send_magic_link_email(email, magic_token, redirect_url)
        if not sent:
            logger.warning(
                "Magic link email NOT sent — the recipient will never receive a sign-in link",
                email=_redact_email(email),
            )
    except Exception:
        logger.exception("Magic link email task failed")


async def send_verification_email_task(
    email: str, verification_token: str, user_name: Optional[str] = None
) -> None:
    """Background-task entrypoint for email verification.

    Takes the CALLER's token deliberately. `EmailService.send_verification_email`
    mints its own token into Redis, but `/auth/verify-email` validates against
    the `email_verifications` table — so the token that got mailed and the token
    that could be verified were never the same value.
    """
    try:
        service = EmailService()
        verification_url = (
            f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
        )
        template_data = {
            "user_name": user_name or email.split("@")[0],
            "verification_url": verification_url,
            "base_url": settings.BASE_URL,
            "company_name": "Janua",
            "support_email": settings.SUPPORT_EMAIL or "support@janua.dev",
        }
        sent = await service._send_email(
            to_email=email,
            subject="Verify your Janua email address",
            html_content=service._render_template("verification.html", template_data),
            text_content=service._render_template("verification.txt", template_data),
        )
        if not sent:
            logger.warning(
                "Verification email NOT sent", email=_redact_email(email)
            )
    except Exception:
        logger.exception("Verification email task failed")
