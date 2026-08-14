"""Locale negotiation for inbound requests.

`users.locale` has existed on the model and in the schema since 000_init, and
`PATCH /api/v1/users/me` can write it — but no signup path ever set it, so the
column is NULL for essentially every row and every downstream consumer falls
through to a deployment default. This module is the piece that was missing:
turning what a client already tells us into a stored preference.

Two rules govern everything here:

1. **Only store a language we actually support.** Persisting `fr-CA` because a
   browser asked for it manufactures a user whose experience is *worse* than
   the default — the default has translations, `fr` does not. Unsupported tags
   resolve to None so the caller stores NULL and the configured default
   applies.
2. **Never make locale required.** A missing or malformed `Accept-Language`
   header returns None. Signup must not care.

Note on regional variants: a tag is reduced to its bare language subtag
(`es-MX`, `es_419`, `ES-mx` all mean `es`) because a translation set is
per-language and regional variants share it.
"""

from typing import Any, List, Optional, Tuple

# Languages with a real translation set behind them. Keep this in step with
# whatever renders user-facing copy; storing a tag no renderer can honor is
# the failure mode this module exists to prevent.
SUPPORTED_LOCALES: Tuple[str, ...] = ("es", "en")

# Accept-Language is attacker-controlled and unbounded. Parse a sane prefix
# rather than walking a megabyte of comma-separated junk.
_MAX_HEADER_CHARS = 512
_MAX_HEADER_ENTRIES = 32


def normalize_locale(raw: Any) -> Optional[str]:
    """Reduce a locale tag to a supported bare language subtag.

    Accepts the shapes that actually appear in stored profiles and in
    Accept-Language headers: ``es``, ``es-MX``, ``es_MX``, ``ES-mx``,
    ``es-419``. Returns None for anything unsupported or unparseable so
    callers fall through to the next tier instead of silently committing to a
    language nobody can render.
    """
    if not raw or not isinstance(raw, str):
        return None
    # BCP 47 separates with "-"; POSIX-style profile values use "_".
    language = raw.strip().replace("_", "-").split("-", 1)[0].lower()
    if language in SUPPORTED_LOCALES:
        return language
    return None


def _parse_accept_language(header: str) -> List[str]:
    """Return the header's language tags ordered by declared preference.

    Implements the parts of RFC 9110 §12.5.4 that change the outcome:
    q-values order the list, ``q=0`` means "explicitly not acceptable" and is
    dropped entirely, and ties keep their original left-to-right order (a
    stable sort), which is what makes ``en-US,en`` behave as written.
    Malformed q-values are treated as a rejection rather than a preference —
    a client that cannot format a float is not expressing a language it wants.
    """
    ranked: List[Tuple[float, int, str]] = []

    for index, part in enumerate(header[:_MAX_HEADER_CHARS].split(",")):
        if index >= _MAX_HEADER_ENTRIES:
            break
        pieces = part.split(";")
        tag = pieces[0].strip()
        if not tag:
            continue

        quality = 1.0
        for param in pieces[1:]:
            param = param.strip()
            if param[:2].lower() != "q=":
                continue  # charset/other params carry no ordering information
            try:
                quality = float(param[2:])
            except ValueError:
                quality = 0.0
            break

        if quality <= 0:
            continue
        # Negated quality sorts highest-first; index breaks ties in place.
        ranked.append((-quality, index, tag))

    ranked.sort()
    return [tag for _, _, tag in ranked]


def locale_from_accept_language(header: Any) -> Optional[str]:
    """Pick the client's most-preferred *supported* language, or None.

    Walks the client's ranked preferences and returns the first tag we can
    actually render. ``*`` is skipped rather than matched: a wildcard says
    "anything is fine", which is an absence of preference, and absence must
    fall through to the deployment default rather than pin the row to
    whichever language happens to be first in SUPPORTED_LOCALES.
    """
    if not header or not isinstance(header, str):
        return None

    for tag in _parse_accept_language(header):
        if tag == "*":
            continue
        normalized = normalize_locale(tag)
        if normalized:
            return normalized
    return None


def locale_from_request(request: Any = None, explicit: Any = None) -> Optional[str]:
    """Resolve the locale to persist for a user being created, or None.

    Precedence, highest first:

    1. ``explicit`` — a locale field on the request body, when the endpoint
       offers one. A client that names its language outranks a header the
       browser filled in.
    2. ``Accept-Language`` on the request.
    3. None — store NULL and let the configured default apply. This is a
       legitimate outcome, not a failure: it keeps the user on the default
       instead of freezing today's guess into the row.

    Returning None rather than raising is the whole contract — no creation
    path may fail because a header was absent, malformed, or hostile.
    """
    normalized = normalize_locale(explicit)
    if normalized:
        return normalized

    if request is None:
        return None

    headers = getattr(request, "headers", None)
    if headers is None:
        return None

    try:
        header_value = headers.get("accept-language")
    except Exception:  # pragma: no cover - defensive: non-mapping headers
        return None

    return locale_from_accept_language(header_value)
