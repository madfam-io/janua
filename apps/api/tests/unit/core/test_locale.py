"""Locale negotiation from Accept-Language.

The rule under test throughout: only a language we can actually render may be
stored, and an absent or hostile header must never be an error.
"""

from types import SimpleNamespace

from app.core.locale import (
    SUPPORTED_LOCALES,
    locale_from_accept_language,
    locale_from_request,
    normalize_locale,
)


def _req(accept_language=None):
    """A stand-in request exposing only what the negotiator reads."""
    headers = {}
    if accept_language is not None:
        headers["accept-language"] = accept_language
    return SimpleNamespace(headers=headers)


class TestNormalize:
    def test_bare_tag(self):
        assert normalize_locale("es") == "es"
        assert normalize_locale("en") == "en"

    def test_region_stripped(self):
        # A translation set is per-language; regional variants share it.
        assert normalize_locale("es-MX") == "es"
        assert normalize_locale("es_MX") == "es"
        assert normalize_locale("ES-mx") == "es"
        assert normalize_locale("es-419") == "es"
        assert normalize_locale("en-GB") == "en"

    def test_unsupported(self):
        # Storing these would give the user a WORSE experience than the
        # default, which at least has translations.
        for tag in ("fr", "fr-CA", "de", "pt-BR", "zh-Hans"):
            assert normalize_locale(tag) is None

    def test_junk(self):
        for tag in (None, "", "   ", 42, [], {}, "-", "!!"):
            assert normalize_locale(tag) is None


class TestHeader:
    def test_simple(self):
        assert locale_from_accept_language("es") == "es"
        assert locale_from_accept_language("en-US") == "en"

    def test_q_order(self):
        # Lower q must lose regardless of position in the string.
        assert locale_from_accept_language("en;q=0.2,es;q=0.9") == "es"
        assert locale_from_accept_language("es;q=0.1,en;q=0.8") == "en"

    def test_implicit_q_wins(self):
        # A tag with no q= is q=1 and outranks an explicit 0.9.
        assert locale_from_accept_language("es;q=0.9,en") == "en"

    def test_tie_keeps_order(self):
        assert locale_from_accept_language("es;q=0.5,en;q=0.5") == "es"
        assert locale_from_accept_language("en;q=0.5,es;q=0.5") == "en"

    def test_skips_unsupported(self):
        # French ranks highest but we cannot render it; fall to the best
        # supported tag rather than to the default.
        assert locale_from_accept_language("fr-CA,fr;q=0.9,es;q=0.4") == "es"

    def test_all_unsupported(self):
        assert locale_from_accept_language("fr-CA,de;q=0.9,ja;q=0.8") is None

    def test_q_zero_rejected(self):
        # q=0 means "not acceptable" — honouring it is the difference between
        # respecting the client and ignoring it.
        assert locale_from_accept_language("es;q=0,en;q=0.5") == "en"
        assert locale_from_accept_language("es;q=0") is None

    def test_wildcard(self):
        # "*" is an absence of preference, so it must fall through to the
        # deployment default rather than pin the row to a guess.
        assert locale_from_accept_language("*") is None
        assert locale_from_accept_language("fr,*;q=0.5") is None
        assert locale_from_accept_language("*;q=0.1,es;q=0.9") == "es"

    def test_whitespace(self):
        assert locale_from_accept_language("  es-MX , en ; q=0.8 ") == "es"

    def test_bad_q(self):
        # A client that cannot format a float is not expressing a preference.
        assert locale_from_accept_language("es;q=bogus,en") == "en"

    def test_junk_header(self):
        for header in (None, "", "   ", ",,,", ";q=1", 42, b"es"):
            assert locale_from_accept_language(header) is None

    def test_long_header(self):
        # Attacker-controlled and unbounded: must terminate, not hang.
        assert locale_from_accept_language("fr," * 5000 + "es") is None
        assert locale_from_accept_language("es," + "fr," * 5000) == "es"


class TestFromRequest:
    def test_header_used(self):
        assert locale_from_request(_req("es-MX,es;q=0.9")) == "es"

    def test_explicit_wins(self):
        # A client that names its language outranks the browser's header.
        assert locale_from_request(_req("en"), explicit="es-MX") == "es"

    def test_bad_explicit(self):
        # An unsupported explicit value must not shadow a usable header.
        assert locale_from_request(_req("es"), explicit="fr-CA") == "es"

    def test_no_header(self):
        # The whole contract: absence is a legitimate answer, not a failure.
        assert locale_from_request(_req()) is None
        assert locale_from_request(None) is None
        assert locale_from_request(_req(None), explicit=None) is None

    def test_unsupported_not_stored(self):
        assert locale_from_request(_req("fr-CA,de;q=0.8"), explicit="pt") is None

    def test_headerless_object(self):
        assert locale_from_request(SimpleNamespace()) is None


def test_supported_set():
    # Guards against a tag being added here without translations behind it.
    assert set(SUPPORTED_LOCALES) == {"es", "en"}
