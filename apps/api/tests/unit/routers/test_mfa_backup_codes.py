"""Unit tests for MFA backup-code hashing + single-use consumption.

Guards the 2026-08-23 security fix: backup codes are hashed at rest (were
plaintext), verified in constant time, consumed exactly once, and the check is
backward-compatible with legacy plaintext entries so live users are not locked
out. Pure functions — no DB, no app bootstrap.
"""

from types import SimpleNamespace

from app.routers.v1.mfa import (
    consume_backup_code,
    generate_backup_codes,
    hash_backup_code,
    _entry_matches_code,
    _normalize_backup_code,
)


def _user(entries):
    """A minimal stand-in for the User ORM object (only mfa_backup_codes used)."""
    return SimpleNamespace(mfa_backup_codes=entries)


class TestHashing:
    def test_hash_is_not_plaintext(self):
        code = "ABCD-1234"
        h = hash_backup_code(code)
        assert code not in h
        assert _normalize_backup_code(code) not in h
        assert h.startswith("$2")  # bcrypt marker

    def test_hash_verifies_the_code_ignoring_dashes_and_case(self):
        h = hash_backup_code("ABCD-1234")
        assert _entry_matches_code({"hash": h}, "ABCD-1234")
        assert _entry_matches_code({"hash": h}, "abcd1234")  # normalized
        assert _entry_matches_code({"hash": h}, "ABCD1234")
        assert not _entry_matches_code({"hash": h}, "ABCD-9999")

    def test_distinct_codes_distinct_hashes(self):
        assert hash_backup_code("ABCD-1234") != hash_backup_code("EFGH-5678")

    def test_generated_codes_are_formatted_and_unique(self):
        codes = generate_backup_codes(10)
        assert len(codes) == 10
        assert len(set(codes)) == 10
        for c in codes:
            assert len(c) == 9 and c[4] == "-"


class TestConsume:
    def test_consumes_a_hashed_code_exactly_once(self):
        code = "WXYZ-7777"
        user = _user([{"hash": hash_backup_code(code), "used": False}])
        assert consume_backup_code(user, code) is True
        # marked used, plaintext never present
        assert user.mfa_backup_codes[0]["used"] is True
        assert "code" not in user.mfa_backup_codes[0]
        # second use is refused (single-use)
        assert consume_backup_code(user, code) is False

    def test_wrong_code_is_refused_and_consumes_nothing(self):
        user = _user([{"hash": hash_backup_code("AAAA-1111"), "used": False}])
        assert consume_backup_code(user, "BBBB-2222") is False
        assert user.mfa_backup_codes[0]["used"] is False

    def test_already_used_code_is_refused(self):
        # Regression: disable_mfa previously ignored the `used` flag entirely.
        code = "USED-0000"
        user = _user([{"hash": hash_backup_code(code), "used": True}])
        assert consume_backup_code(user, code) is False

    def test_only_the_matching_entry_is_consumed(self):
        c1, c2 = "AAAA-1111", "BBBB-2222"
        user = _user(
            [
                {"hash": hash_backup_code(c1), "used": False},
                {"hash": hash_backup_code(c2), "used": False},
            ]
        )
        assert consume_backup_code(user, c2) is True
        assert user.mfa_backup_codes[0]["used"] is False  # c1 untouched
        assert user.mfa_backup_codes[1]["used"] is True

    def test_empty_or_missing_codes(self):
        assert consume_backup_code(_user([]), "X") is False
        assert consume_backup_code(_user(None), "X") is False


class TestBackwardCompat:
    """Existing rows carry plaintext {"code": ...} (or a bare string). They must
    still validate (no lockout) and be upgraded to used-without-plaintext on spend."""

    def test_legacy_dict_plaintext_still_validates_once(self):
        user = _user([{"code": "LEGA-CY01", "used": False}])
        assert consume_backup_code(user, "LEGA-CY01") is True
        assert user.mfa_backup_codes[0]["used"] is True
        assert "code" not in user.mfa_backup_codes[0]  # plaintext dropped on consume
        assert consume_backup_code(user, "LEGA-CY01") is False

    def test_legacy_bare_string_still_validates(self):
        user = _user(["BARE-9999"])
        assert consume_backup_code(user, "bare9999") is True
        assert user.mfa_backup_codes[0]["used"] is True

    def test_legacy_used_flag_respected(self):
        user = _user([{"code": "SPEN-T000", "used": True}])
        assert consume_backup_code(user, "SPEN-T000") is False
