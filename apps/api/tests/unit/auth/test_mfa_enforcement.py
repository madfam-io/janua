"""Unit tests for the shared MFA-enforcement gate (2026-08-23).

Guards the decision that fixes the audit's #1 P0 — MFA was bypassed on every
login path except JSON /signin. The gate must be OFF by default (so shipping it
cannot lock anyone out) and only True when BOTH the flag is on AND the user has
MFA configured. Pure functions — no DB, no app bootstrap.
"""

from types import SimpleNamespace

import jwt as pyjwt

from app.auth.mfa_enforcement import (
    MFA_CHALLENGE_TYPE,
    mfa_required_for,
    mint_mfa_challenge_token,
)
from app.config import settings


def _user(mfa_enabled=True, mfa_secret="SECRET"):
    return SimpleNamespace(id="u-1", mfa_enabled=mfa_enabled, mfa_secret=mfa_secret)


class TestGateDefaultOff:
    def test_off_by_default_even_with_mfa_enabled(self, monkeypatch):
        # The flag defaults False; with it off, NO login path is interrupted —
        # this is the property that makes shipping enforcement lock-out-safe.
        monkeypatch.setattr(settings, "MFA_ENFORCE_ON_LOGIN", False, raising=False)
        assert mfa_required_for(_user(mfa_enabled=True)) is False

    def test_on_and_enabled_requires_mfa(self, monkeypatch):
        monkeypatch.setattr(settings, "MFA_ENFORCE_ON_LOGIN", True, raising=False)
        assert mfa_required_for(_user(mfa_enabled=True, mfa_secret="S")) is True

    def test_on_but_user_has_no_mfa_does_not_require(self, monkeypatch):
        monkeypatch.setattr(settings, "MFA_ENFORCE_ON_LOGIN", True, raising=False)
        assert mfa_required_for(_user(mfa_enabled=False, mfa_secret=None)) is False
        assert mfa_required_for(_user(mfa_enabled=True, mfa_secret=None)) is False


class TestChallengeToken:
    def test_token_is_a_challenge_not_a_session(self, monkeypatch):
        monkeypatch.setattr(settings, "MFA_ENFORCE_ON_LOGIN", True, raising=False)
        token = mint_mfa_challenge_token(_user())
        decoded = pyjwt.decode(
            token,
            settings.JWT_SECRET_KEY or "development-secret-key",
            algorithms=["HS256"],
            options={"verify_iss": False},
        )
        assert decoded["type"] == MFA_CHALLENGE_TYPE
        assert decoded["sub"] == "u-1"
        assert "exp" in decoded and "iat" in decoded
