"""Locale resolution and localized strings for transactional email.

The mail path had no notion of language at all: subjects were string literals
at each call site and every template was English-only. That made English the
first thing every recipient saw, regardless of who they are — which is wrong
for a user base that is predominantly Mexican.

Three moving parts live here so the email service stays about *sending*:

1. `resolve_locale` — per-recipient language with an explicit precedence.
2. `subject_for`   — the subject line, keyed by message rather than hardcoded.
3. `template_candidates` — the localized template name, with English as the
   fallback so a locale that has not been translated yet still sends a real
   message instead of failing.

Locale tags are normalized to a bare language subtag (`es-MX`, `es_419`,
`ES-mx` all mean `es`), because a translation set is per-language; regional
variants share it. The Spanish copy is written for es-MX specifically.
"""

from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, pass_context

# Languages that have a full translation set. Order is not significant.
SUPPORTED_LOCALES: tuple = ("es", "en")

# English is the fallback for any string a locale has not translated yet —
# never an empty body.
FALLBACK_LOCALE = "en"

# Client-facing mail defaults to Spanish: this platform's users are
# predominantly Mexican, so English is the wrong default even though it was
# the only option before. Overridable per-deployment via DEFAULT_EMAIL_LOCALE
# and per-message via the `locale` argument.
DEFAULT_LOCALE = "es"


def normalize_locale(raw: Any) -> Optional[str]:
    """Reduce a locale tag to a supported bare language subtag.

    Accepts the shapes that actually show up in stored user profiles and
    Accept-Language headers: `es`, `es-MX`, `es_MX`, `ES-mx`, `es-419`.
    Returns None for anything unsupported or unparseable so callers can fall
    through to the next precedence tier rather than silently picking a
    language nobody asked for.
    """
    if not raw or not isinstance(raw, str):
        return None
    # Split on both separators; BCP 47 uses "-", POSIX-style profiles use "_".
    language = raw.strip().replace("_", "-").split("-", 1)[0].lower()
    if language in SUPPORTED_LOCALES:
        return language
    return None


def resolve_locale(
    explicit: Any = None,
    user: Any = None,
    default: Any = None,
) -> str:
    """Resolve the language for one recipient, highest precedence first.

    1. `explicit` — what the caller passed. A caller that knows the audience
       (an invitation addressed to a specific person, an operator-triggered
       resend) always wins.
    2. `user.locale` — the recipient's stored preference. `users.locale`
       exists on the model and in the schema, so this is a real column and
       not an aspiration; it is nullable and unset for most rows today.
    3. `default` — the deployment default (DEFAULT_EMAIL_LOCALE).
    4. `DEFAULT_LOCALE` — es-MX.

    Each tier is skipped when it is absent OR unsupported, so a stored
    `fr-CA` does not shadow the configured default with an untranslated
    language.
    """
    for candidate in (
        explicit,
        getattr(user, "locale", None) if user is not None else None,
        default,
    ):
        normalized = normalize_locale(candidate)
        if normalized:
            return normalized
    return DEFAULT_LOCALE


def template_candidates(template_name: str, locale: str) -> List[str]:
    """Template names to try, most specific first.

    Localized templates live in a per-language subdirectory
    (`templates/email/es/magic_link.html`); English stays at the root, where
    it already is. The loader is rooted at `templates/email`, so a template
    under `es/` still resolves `{% extends "base.html" %}` to the one shared
    base — the subdirectory changes nothing about inheritance.

    English is always appended last: a message with no translation yet sends
    in English rather than raising.
    """
    if locale == FALLBACK_LOCALE:
        return [template_name]
    return [f"{locale}/{template_name}", template_name]


# --------------------------------------------------------------------------
# Subjects
#
# Keyed by message so the call sites stop carrying English string literals.
# es-MX business register: usted-form, "correo electrónico", "iniciar sesión".
# --------------------------------------------------------------------------
SUBJECTS: Dict[str, Dict[str, str]] = {
    "verification": {
        "en": "Verify your Janua account",
        "es": "Verifique su cuenta de Janua",
    },
    "password_reset": {
        "en": "Reset your Janua password",
        "es": "Restablezca su contraseña de Janua",
    },
    "magic_link": {
        "en": "Your Janua sign-in link",
        "es": "Su enlace de acceso a Janua",
    },
    "welcome": {
        "en": "Welcome to Janua!",
        "es": "Le damos la bienvenida a Janua",
    },
    "invitation": {
        "en": "You're invited to join {organization_name} on Janua",
        "es": "Le invitaron a unirse a {organization_name} en Janua",
    },
}


def subject_for(message_key: str, locale: Optional[str] = None, **fields: Any) -> str:
    """Return the localized subject for a message.

    Falls back to English when the locale has no translation for this
    message, and to the message key itself only if the key is unknown — an
    unknown key is a programming error, and a visible one beats an email with
    an empty subject line.
    """
    per_locale = SUBJECTS.get(message_key)
    if not per_locale:
        return message_key
    resolved = normalize_locale(locale) or FALLBACK_LOCALE
    template = per_locale.get(resolved) or per_locale[FALLBACK_LOCALE]
    if fields:
        try:
            return template.format(**fields)
        except (KeyError, IndexError):
            return template
    return template


# --------------------------------------------------------------------------
# Shared chrome
#
# base.html's header and footer are outside every {% block content %}, so
# localized bodies would otherwise sit inside an English frame. These strings
# are exposed to templates as `t('key')` rather than duplicating base.html.
# --------------------------------------------------------------------------
CHROME: Dict[str, Dict[str, str]] = {
    "en": {
        # The header now reads MADFAM on every message, so the tagline is
        # MADFAM's rather than one platform's.
        "tagline": "Technology, engineered for your operation",
        "rights": "All rights reserved.",
        "powered_by": "Powered by",
        "privacy": "Privacy Policy",
        "terms": "Terms of Service",
        "support": "Support",
        "why_received": "You received this email because you have an account with Janua.",
        "location": "Innovaciones MADFAM (MADFAM) • Mexico City, Mexico",
    },
    "es": {
        "tagline": "Tecnología, diseñada para tu operación",
        "rights": "Todos los derechos reservados.",
        # "Con tecnología de" is the standard es-MX rendering of "Powered by".
        # "Impulsado por" reads as marketing; this reads as an attribution.
        "powered_by": "Con tecnología de",
        "privacy": "Aviso de privacidad",
        "terms": "Términos del servicio",
        "support": "Soporte",
        "why_received": "Recibió este correo electrónico porque tiene una cuenta en Janua.",
        "location": "Innovaciones MADFAM (MADFAM) • Ciudad de México, México",
    },
}


def chrome_string(key: str, locale: Optional[str] = None) -> str:
    """Look up a shared header/footer string.

    Defaults to English when no locale is in scope so that rendering a
    template directly — without going through the service, as the template
    guards in the test suite do — produces exactly the frame it produced
    before localization existed.
    """
    resolved = normalize_locale(locale) or FALLBACK_LOCALE
    return CHROME.get(resolved, CHROME[FALLBACK_LOCALE]).get(
        key, CHROME[FALLBACK_LOCALE].get(key, "")
    )


def html_lang(locale: Optional[str] = None) -> str:
    """The `lang` attribute for <html>, so screen readers and clients that
    offer translation see the real language of the message."""
    resolved = normalize_locale(locale) or FALLBACK_LOCALE
    return "es-MX" if resolved == "es" else "en"


@pass_context
def _chrome_global(ctx, key: str) -> str:
    """`t('key')` inside a template: the shared header/footer strings.

    Context-aware so base.html renders in the same language as the body
    without every template forwarding the locale explicitly. With no locale in
    context — a template rendered directly rather than through a service —
    this yields the English frame the templates had before localization.
    """
    return chrome_string(key, ctx.get("locale"))


@pass_context
def _lang_global(ctx) -> str:
    """`lang()` inside a template: the <html lang> attribute value."""
    return html_lang(ctx.get("locale"))


def install_template_globals(env: Environment) -> Environment:
    """Register the globals `templates/email/base.html` depends on.

    base.html calls `t()` and `lang()`, and Jinja raises on calling an
    undefined name — so any environment that loads these templates must have
    them. Three services build their own environment over this same
    directory; routing them all through `build_email_environment` keeps that
    from being something a fourth one can forget.
    """
    env.globals["t"] = _chrome_global
    env.globals["lang"] = _lang_global
    return env


def build_email_environment(template_dir: Any) -> Environment:
    """The Jinja environment for `templates/email`, globals included."""
    return install_template_globals(
        Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    )
