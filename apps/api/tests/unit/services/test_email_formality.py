"""Guards for the Spanish register (`tú` / `usted`) of transactional email.

Spanish forces a choice English does not: every sentence addressed at the
reader is either `tú` or `usted`, with no neutral second person. The failure
mode this file exists to prevent is not a crash — it is a perfectly
well-formed email that addresses a clinic's patient in the wrong register, or
worse, addresses them in BOTH inside one message because someone added a
paragraph and only wrote one variant.

That failure is invisible to every other kind of test: the template renders,
the send succeeds, the API returns 200. So the assertions here are about the
TEXT A READER SEES, and three of them are structural rather than
example-based, because an example-based test only covers the strings someone
remembered to write an example for:

* `TestCatalogPartition` — every Spanish string is either declared
  register-sensitive (both variants present) or declared register-neutral.
  A key that is neither fails, which is what makes forgetting impossible.
* `TestNoRegisterLeakInCatalog` — a `tú` string containing usted markers (or
  vice versa) is a half-done translation. Scanned, not eyeballed.
* `TestTemplateLiteralsAreRegisterNeutral` — prose left inline in an `es/`
  template can never follow the reader's choice, so inline prose must not
  address the reader at all.

The rest render the real templates in both registers and assert on the
output, because reading a diff does not tell you what the reader gets.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.email_i18n import (
    CHROME,
    DEFAULT_FORMALITY,
    ES_REGISTER_NEUTRAL,
    ES_STRINGS,
    ES_TU,
    FORMALITY_TU,
    FORMALITY_USTED,
    SUBJECTS,
    SUBJECTS_ES_TU,
    build_email_environment,
    chrome_string,
    normalize_formality,
    resolve_formality,
    subject_for,
)
from app.services.email_service import EmailService

# tests/unit/services/<this file> -> apps/api
API_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = API_ROOT / "app" / "templates" / "email"
ES_TEMPLATE_DIR = TEMPLATE_DIR / "es"

# Enough context that every button has an href and every optional block renders.
TEMPLATE_CONTEXT = {
    "user_name": "Ana",
    "user_email": "ana@clinica.test",
    "magic_link": "https://example.test/go?token=abc",
    "magic_url": "https://example.test/go?token=abc",
    "reset_link": "https://example.test/go?token=abc",
    "reset_url": "https://example.test/go?token=abc",
    "reset_code": "123456",
    "verification_code": "654321",
    "verification_link": "https://example.test/go?token=abc",
    "verification_url": "https://example.test/go?token=abc",
    "dashboard_link": "https://example.test/app",
    "dashboard_url": "https://example.test/app",
    "invitation_url": "https://example.test/invite",
    "inviter_name": "Luis",
    "organization_name": "Clinica Vida",
    "role": "admin",
    "teams": ["Recepcion"],
    "expires_at": "1 de septiembre de 2026",
    "plan_name": "Pro",
    "account_id": "acct_1",
    "request_ip": "203.0.113.10",
    "request_browser": "Safari",
    "request_time": "12:00",
    "support_email": "hola@madfam.io",
    "base_url": "https://janua.dev",
}

# ---------------------------------------------------------------------------
# Register markers.
#
# Spanish marks the register in three places, and a scan has to look at all
# three or it misses the majority of real strings:
#   1. the pronoun itself           usted / tú
#   2. possessives and clitics      su, sus, le, les / tu, tus, te
#   3. the verb ending              "Verifique" vs "Verifica"
#
# (3) cannot be regexed generically, so the usted forms actually used in this
# copy are listed.
#
# Three shapes are DELIBERATELY EXCLUDED, each because a real string tripped
# on it while this was being written:
#
# * Preterites (`creó`, `recibió`, `solicitó`, `hizo`). "Su cuenta se creó
#   correctamente" is third person about the account, not usted about the
#   reader, and it is correct in BOTH registers. Excluding them loses nothing:
#   `why_received` — the one usted string carrying no pronoun — is still
#   caught by `tiene`.
# * A generic enclitic regex (`\\w+arte\\b`). It matches "parte", "aparte",
#   "comparte". The enclitics that appear in real copy attach to infinitives
#   and are few, so they are listed by hand instead.
# * URLs, stripped before scanning: a link ending in `/invite` is not a verb.
#
# `tiene`, `puede` and `necesita` are kept even though third person shares
# them, because dropping them would blind the scan to the most common way
# usted appears without a pronoun. If a genuine third-person sentence ever
# trips one, rewrite the sentence rather than deleting the marker.
# ---------------------------------------------------------------------------
_USTED_VERBS = (
    "abra|acepte|active|añada|cambie|comience|configure|consulte|copie|defina|escriba|"
    "escríbanos|habilite|haga|ignore|inicie|intégrelo|invite|pegue|reciba|restablezca|"
    "revise|solicite|use|verifique|necesita|puede|tiene"
)
_USTED_ENCLITICS = (
    "acompañarle|atenderle|ayudarle|darle|enviarle|hacerle|informarle|mostrarle|"
    "permitirle|tenerle|unirsele"
)
_TU_ENCLITICS = (
    "acompañarte|atenderte|ayudarte|darte|enviarte|hacerte|informarte|mostrarte|"
    "permitirte|tenerte|unirte"
)
USTED_MARKERS = (
    ("pronoun 'usted'", re.compile(r"\busted(?:es)?\b", re.I)),
    ("possessive 'su/sus'", re.compile(r"\bsus?\b", re.I)),
    ("clitic 'le/les'", re.compile(r"\bles?\b", re.I)),
    ("enclitic '-le'", re.compile(rf"\b(?:{_USTED_ENCLITICS})\b", re.I)),
    ("usted verb form", re.compile(rf"\b(?:{_USTED_VERBS})\b", re.I)),
)
TU_MARKERS = (
    ("pronoun 'tú'", re.compile(r"\bt[úu]\b", re.I)),
    ("possessive 'tu/tus'", re.compile(r"\btus?\b", re.I)),
    ("clitic 'te'", re.compile(r"\bte\b", re.I)),
    ("enclitic '-te'", re.compile(rf"\b(?:{_TU_ENCLITICS})\b", re.I)),
)


def markers_found(text: str, markers) -> list[str]:
    """Names of the register markers present in `text`."""
    return [name for name, pattern in markers if pattern.search(text)]


def visible_text(rendered: str) -> str:
    """The words a reader actually sees: markup, CSS and URLs stripped.

    Scanning raw HTML for `\\ble\\b` would hit attribute values and stylesheet
    text; scanning the visible text cannot. URLs go too — a path segment is
    not prose, and `https://example.test/invite` is not the usted imperative
    "invite". `.txt` templates lose only their URLs, having no tags.
    """
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", rendered, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b(?:https?://|www\.)\S+", " ", text)
    return re.sub(r"\s+", " ", text)


def template_literal_text(source: str) -> str:
    """Visible text of a template with every Jinja construct removed.

    What survives is exactly the prose hardcoded in the file — the prose that
    can never follow the reader's register, because `t()` never sees it.
    """
    stripped = re.sub(r"\{[{%#].*?[}%#]\}", " ", source, flags=re.S)
    return visible_text(stripped)


@pytest.fixture(scope="module")
def env():
    return build_email_environment(TEMPLATE_DIR)


def render_es(env, template_name: str, formality: str) -> str:
    context = {
        **TEMPLATE_CONTEXT,
        "current_year": 2026,
        "subject": "Asunto",
        "locale": "es",
        "legal_locale": "es",
        "formality": formality,
    }
    return env.get_template(f"es/{template_name}").render(**context)


ES_TEMPLATE_NAMES = sorted(p.name for p in ES_TEMPLATE_DIR.iterdir() if p.is_file())


class TestCatalogPartition:
    """Every Spanish key is explicitly register-sensitive or register-neutral.

    This is the test that makes forgetting impossible. Adding a Spanish string
    that addresses the reader and writing only the usted half leaves its key
    in neither ES_TU nor ES_REGISTER_NEUTRAL, and this fails.
    """

    def test_every_spanish_key_declares_its_register_handling(self):
        undecided = set(ES_STRINGS) - set(ES_TU) - ES_REGISTER_NEUTRAL
        assert not undecided, (
            "Spanish key(s) with neither a `tú` variant nor a register-neutral "
            f"declaration: {sorted(undecided)}. Add the `tú` wording to ES_TU, or — "
            "if the string reads identically in both registers — add the key to "
            "ES_REGISTER_NEUTRAL with a comment saying why."
        )

    def test_no_tu_variant_without_an_usted_counterpart(self):
        orphans = set(ES_TU) - set(ES_STRINGS)
        assert not orphans, (
            f"`tú` variant(s) for key(s) that have no usted string: {sorted(orphans)}. "
            "usted is the fallback register, so an orphan `tú` string is "
            "unreachable for anyone who has not opted in."
        )

    def test_a_key_is_not_both_sensitive_and_neutral(self):
        contradictory = set(ES_TU) & ES_REGISTER_NEUTRAL
        assert not contradictory, (
            f"key(s) declared register-neutral but also given a `tú` variant: "
            f"{sorted(contradictory)}"
        )

    def test_neutral_keys_exist(self):
        missing = ES_REGISTER_NEUTRAL - set(ES_STRINGS)
        assert not missing, (
            f"ES_REGISTER_NEUTRAL names key(s) that no longer exist: {sorted(missing)}"
        )

    def test_every_spanish_subject_has_both_registers(self):
        spanish_subjects = {key for key, per_locale in SUBJECTS.items() if "es" in per_locale}
        assert spanish_subjects == set(SUBJECTS_ES_TU), (
            "Every Spanish subject addresses the reader, so every one needs a `tú` "
            f"variant. usted-only: {sorted(spanish_subjects - set(SUBJECTS_ES_TU))}; "
            f"orphan tú: {sorted(set(SUBJECTS_ES_TU) - spanish_subjects)}"
        )

    def test_vosotros_is_not_a_supported_register(self):
        """Peninsular Spanish reads as foreign or comic to a Mexican reader.

        Pinned as a test so re-adding it is a deliberate act with a failing
        test to delete, not a quiet dict entry.
        """
        assert normalize_formality("vosotros") is None
        assert "vosotros" not in ES_TU
        assert not any("vosotros" in str(v).lower() for v in ES_STRINGS.values())


class TestNoRegisterLeakInCatalog:
    """A half-translated string still renders; only a scan catches it."""

    @pytest.mark.parametrize("key", sorted(ES_TU))
    def test_tu_strings_carry_no_usted_markers(self, key):
        found = markers_found(ES_TU[key], USTED_MARKERS)
        assert not found, f"`tú` string {key!r} still contains {found}: {ES_TU[key]!r}"

    @pytest.mark.parametrize("key", sorted(set(ES_STRINGS) - ES_REGISTER_NEUTRAL))
    def test_usted_strings_carry_no_tu_markers(self, key):
        found = markers_found(ES_STRINGS[key], TU_MARKERS)
        assert not found, f"usted string {key!r} contains {found}: {ES_STRINGS[key]!r}"

    @pytest.mark.parametrize("key", sorted(ES_REGISTER_NEUTRAL))
    def test_neutral_strings_address_nobody(self, key):
        value = ES_STRINGS[key]
        found = markers_found(value, USTED_MARKERS) + markers_found(value, TU_MARKERS)
        assert not found, (
            f"key {key!r} is declared register-neutral but its wording is "
            f"register-marked ({found}): {value!r}. Either rewrite it so it names a "
            "thing instead of addressing the reader, or move it out of "
            "ES_REGISTER_NEUTRAL and give it a `tú` variant."
        )


class TestTemplateLiteralsAreRegisterNeutral:
    """Prose hardcoded in a template can never follow the reader's choice."""

    @pytest.mark.parametrize("name", ES_TEMPLATE_NAMES)
    def test_no_register_marked_prose_outside_t(self, name):
        literals = template_literal_text((ES_TEMPLATE_DIR / name).read_text())
        found = markers_found(literals, USTED_MARKERS) + markers_found(literals, TU_MARKERS)
        assert not found, (
            f"es/{name} hardcodes register-marked Spanish ({found}) outside a t() call, "
            "so it renders the same way whichever register the reader chose. Move the "
            f"sentence into ES_BODY/ES_TU and reference it with t(). Literal text: "
            f"{literals.strip()[:400]!r}"
        )

    @pytest.mark.parametrize("name", ES_TEMPLATE_NAMES + ["../base.html"])
    def test_every_referenced_key_resolves_in_both_registers(self, name):
        """A missing key renders as an empty string, i.e. a blank paragraph."""
        source = (ES_TEMPLATE_DIR / name).read_text()
        keys = set(re.findall(r"\bt\(\s*['\"]([^'\"]+)['\"]\s*\)", source))
        assert keys, f"{name} references no t() keys — did the key syntax change?"
        for key in sorted(keys):
            for formality in (FORMALITY_USTED, FORMALITY_TU):
                value = chrome_string(key, "es", formality)
                assert value, (
                    f"{name} calls t({key!r}) but it resolves to an empty string in "
                    f"{formality!r} — the message would ship with a blank line there."
                )


class TestNormalizeFormality:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("tu", FORMALITY_TU),
            ("tú", FORMALITY_TU),
            ("TU", FORMALITY_TU),
            ("  Tú  ", FORMALITY_TU),
            ("usted", FORMALITY_USTED),
            ("USTED", FORMALITY_USTED),
            ("Ud.", None),
            ("vosotros", None),
            ("vos", None),
            ("", None),
            (None, None),
            (7, None),
            (["tu"], None),
        ],
    )
    def test_normalizes_or_rejects(self, raw, expected):
        assert normalize_formality(raw) == expected


class TestResolveFormality:
    def test_default_is_usted(self):
        """The safe register for someone who has told us nothing."""
        assert resolve_formality() == FORMALITY_USTED
        assert DEFAULT_FORMALITY == FORMALITY_USTED

    def test_null_column_means_not_chosen_not_tu(self):
        user = SimpleNamespace(spanish_formality=None)
        assert resolve_formality(user=user) == FORMALITY_USTED

    def test_stored_choice_is_honoured(self):
        user = SimpleNamespace(spanish_formality="tu")
        assert resolve_formality(user=user) == FORMALITY_TU

    def test_explicit_argument_outranks_stored_choice(self):
        user = SimpleNamespace(spanish_formality="usted")
        assert resolve_formality(FORMALITY_TU, user=user) == FORMALITY_TU

    def test_unrecognized_stored_value_falls_through_to_usted(self):
        """Including 'vosotros' — a bad row must not raise, and must not guess."""
        for stored in ("vosotros", "VOS", "", "  ", "nope"):
            user = SimpleNamespace(spanish_formality=stored)
            assert resolve_formality(user=user) == FORMALITY_USTED

    def test_user_without_the_attribute_does_not_raise(self):
        """Rows loaded before the column existed, and non-User callers."""
        assert resolve_formality(user=SimpleNamespace()) == FORMALITY_USTED


class TestUstedIsTheFallbackRegister:
    def test_absent_tu_variant_falls_back_to_usted_not_to_english(self):
        """A key with no `tú` wording must still render Spanish."""
        neutral_key = sorted(ES_REGISTER_NEUTRAL)[0]
        assert neutral_key not in ES_TU
        assert chrome_string(neutral_key, "es", FORMALITY_TU) == ES_STRINGS[neutral_key]
        assert chrome_string(neutral_key, "es", FORMALITY_TU) != CHROME["en"].get(neutral_key)

    def test_unknown_formality_renders_usted(self):
        assert chrome_string("why_received", "es", "vosotros") == ES_STRINGS["why_received"]
        assert chrome_string("why_received", "es", None) == ES_STRINGS["why_received"]

    def test_formality_does_not_leak_into_english(self):
        assert chrome_string("why_received", "en", FORMALITY_TU) == CHROME["en"]["why_received"]


class TestSubjects:
    @pytest.mark.parametrize("key", sorted(SUBJECTS_ES_TU))
    def test_spanish_subject_follows_the_register(self, key):
        usted = subject_for(key, "es", FORMALITY_USTED, organization_name="Clinica Vida")
        informal = subject_for(key, "es", FORMALITY_TU, organization_name="Clinica Vida")
        assert usted != informal
        assert not markers_found(informal, USTED_MARKERS)
        assert not markers_found(usted, TU_MARKERS)

    def test_interpolation_survives_the_register_switch(self):
        subject = subject_for("invitation", "es", FORMALITY_TU, organization_name="Clinica Vida")
        assert "Clinica Vida" in subject
        assert "{organization_name}" not in subject

    def test_default_subject_register_is_usted(self):
        assert subject_for("welcome", "es") == SUBJECTS["welcome"]["es"]

    def test_english_subject_ignores_formality(self):
        assert subject_for("welcome", "en", FORMALITY_TU) == SUBJECTS["welcome"]["en"]


class TestRenderedOutput:
    """The real templates, rendered, asserted on the text a reader sees."""

    @pytest.mark.parametrize("name", ES_TEMPLATE_NAMES)
    def test_tu_render_contains_no_usted(self, env, name):
        text = visible_text(render_es(env, name, FORMALITY_TU))
        found = markers_found(text, USTED_MARKERS)
        assert not found, (
            f"es/{name} rendered for `tú` still addresses the reader as usted: {found}"
        )

    @pytest.mark.parametrize("name", ES_TEMPLATE_NAMES)
    def test_usted_render_contains_no_tu(self, env, name):
        text = visible_text(render_es(env, name, FORMALITY_USTED))
        found = markers_found(text, TU_MARKERS)
        assert not found, f"es/{name} rendered for usted addresses the reader as `tú`: {found}"

    @pytest.mark.parametrize("name", ES_TEMPLATE_NAMES)
    def test_the_two_registers_actually_differ(self, env, name):
        """Catches a template wired to t() for nothing that matters."""
        assert render_es(env, name, FORMALITY_TU) != render_es(env, name, FORMALITY_USTED)

    @pytest.mark.parametrize("name", ES_TEMPLATE_NAMES)
    def test_no_blank_t_output(self, env, name):
        """An unresolved key renders as "" — visible only as a hole in the copy."""
        rendered = render_es(env, name, FORMALITY_TU)
        assert "{{" not in rendered and "{%" not in rendered
        # Two consecutive blank-ish lines where a paragraph should be.
        assert not re.search(r"\n[ \t]*\n[ \t]*\n[ \t]*\n", rendered), (
            f"es/{name} has a run of empty lines, which is what a t() key that "
            "resolved to nothing looks like in the .txt part"
        )

    @pytest.mark.parametrize(
        "name,usted_phrase,tu_phrase",
        [
            # was "Inicie sesión en Janua" / "Inicia sesión en Janua" — the
            # sender-identity branch stopped naming the platform at the reader.
            ("magic_link.html", "Inicie sesión en su portal", "Inicia sesión en tu portal"),
            ("magic_link.txt", "¿Necesita ayuda?", "¿Necesitas ayuda?"),
            ("verification.html", "Verifique su correo", "Verifica tu correo"),
            ("password_reset.html", "Restablezca su contraseña", "Restablece tu contraseña"),
            ("welcome.html", "Le damos la bienvenida", "Te damos la bienvenida"),
            ("welcome.txt", "Comience por su panel", "Comienza por tu panel"),
            ("invitation.html", "Le invitaron a colaborar", "Te invitaron a colaborar"),
            ("invitation.txt", "le invitó a unirse", "te invitó a unirse"),
        ],
    )
    def test_specific_sentences_switch(self, env, name, usted_phrase, tu_phrase):
        usted = render_es(env, name, FORMALITY_USTED)
        informal = render_es(env, name, FORMALITY_TU)
        assert usted_phrase in usted and usted_phrase not in informal
        assert tu_phrase in informal and tu_phrase not in usted

    def test_shared_footer_follows_the_body_register(self, env):
        """base.html sits outside every content block; it must not stay formal."""
        usted = render_es(env, "welcome.html", FORMALITY_USTED)
        informal = render_es(env, "welcome.html", FORMALITY_TU)
        assert "Recibió este correo electrónico porque tiene una cuenta" in usted
        assert "Recibiste este correo electrónico porque tienes una cuenta" in informal

    def test_untouched_footer_elements_are_not_register_dependent(self, env):
        """Another branch owns the sender identity and legal links; this one
        must not move them in either register."""
        for formality in (FORMALITY_USTED, FORMALITY_TU):
            rendered = render_es(env, "welcome.html", formality)
            assert "Innovaciones MADFAM" in rendered
            assert "Aviso de privacidad" in rendered
            assert "Términos del servicio" in rendered

    def test_action_urls_survive_both_registers(self, env):
        """A register switch that blanked a button href would be worse than
        the wrong register."""
        for name in ES_TEMPLATE_NAMES:
            for formality in (FORMALITY_USTED, FORMALITY_TU):
                rendered = render_es(env, name, formality)
                assert "example.test" in rendered, f"es/{name} lost its links in {formality}"


class TestServiceRenderPath:
    """The bare Jinja env above is not what production uses."""

    @pytest.mark.parametrize("formality", [FORMALITY_TU, FORMALITY_USTED])
    def test_service_injects_the_register(self, formality):
        html = EmailService()._render_template(
            "magic_link.html", dict(TEMPLATE_CONTEXT), "es", formality
        )
        expected = "Inicia sesión" if formality == FORMALITY_TU else "Inicie sesión"
        assert expected in html

    def test_service_defaults_to_usted(self):
        html = EmailService()._render_template("magic_link.html", dict(TEMPLATE_CONTEXT), "es")
        # was "Inicie sesión en Janua"
        assert "Inicie sesión en su portal" in html

    def test_english_body_is_unaffected_by_the_register(self):
        """`tú` is a Spanish concept; asking for it must not perturb English."""
        formal = EmailService()._render_template(
            "magic_link.html", dict(TEMPLATE_CONTEXT), "en", FORMALITY_USTED
        )
        informal = EmailService()._render_template(
            "magic_link.html", dict(TEMPLATE_CONTEXT), "en", FORMALITY_TU
        )
        assert formal == informal

    @pytest.mark.parametrize(
        "template_name,url_key,tu_phrase",
        [
            ("verification.html", "verification_url", "Verifica tu correo electrónico"),
            ("magic_link.html", "magic_url", "Inicia sesión en tu portal"),
            ("password_reset.html", "reset_url", "Restablece tu contraseña"),
        ],
    )
    def test_degraded_fallback_body_keeps_the_register(self, template_name, url_key, tu_phrase):
        """The last-resort body is still an email somebody reads."""
        data = {url_key: "https://example.test/go"}
        body = EmailService._fallback_body(template_name, data, "es", FORMALITY_TU)
        assert tu_phrase in body
        assert not markers_found(body, USTED_MARKERS)


class TestUserColumn:
    def test_column_exists_and_is_nullable(self):
        from app.models import User

        column = User.__table__.columns["spanish_formality"]
        assert column.nullable, "NULL must stay expressible: it means 'has not chosen'"
        assert column.type.length >= len(FORMALITY_USTED)

    def test_resolve_reads_the_column_name_the_model_defines(self):
        """Guards a rename on one side of the pair."""
        from app.models import User

        assert "spanish_formality" in User.__table__.columns
        user = SimpleNamespace(spanish_formality=FORMALITY_TU)
        assert resolve_formality(user=user) == FORMALITY_TU


class TestMigration:
    """012 must be re-entrant: one unguarded add_column rolls back the chain."""

    MIGRATION = API_ROOT / "alembic" / "versions" / "012_user_spanish_formality.py"

    def test_migration_exists_and_chains_to_011(self):
        source = self.MIGRATION.read_text()
        assert 'revision = "012_user_spanish_formality"' in source
        assert 'down_revision = "011_invitation_columns"' in source

    def test_add_column_is_guarded_by_an_inspection(self):
        """`Base.metadata.create_all` environments already have the column."""
        source = self.MIGRATION.read_text()
        assert 'inspect(bind).get_columns("users")' in source
        add_column_line = next(
            i for i, line in enumerate(source.splitlines()) if "op.add_column" in line
        )
        guard_line = next(
            i
            for i, line in enumerate(source.splitlines())
            if 'if "spanish_formality" not in existing' in line
        )
        assert guard_line < add_column_line

    def test_downgrade_is_guarded_too(self):
        source = self.MIGRATION.read_text()
        assert 'if "spanish_formality" in existing' in source

    def test_no_backfill(self):
        """Writing 'usted' onto every row would erase the difference between
        'chose usted' and 'never saw the question'."""
        source = self.MIGRATION.read_text()
        assert "UPDATE users" not in source.upper().replace("UPDATE USERS", "UPDATE users")

    def test_revision_id_fits_the_alembic_version_column(self):
        assert len("012_user_spanish_formality") <= 32
