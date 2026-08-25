"""MAGIC_LINK_RATE_LIMIT — the ceremony knob.

The magic-link endpoint is rate-limited per client IP. The default (5/hour)
protects against email-bombing, but a team-onboarding ceremony from one shared
office IP hard-stops at the sixth person. These tests pin the knob: the default
is unchanged, the env override works, and the route reads the setting (not a
hardcoded string).
"""

from pathlib import Path

from app.config import Settings


class TestMagicLinkRateLimitKnob:
    def test_default_is_unchanged_five_per_hour(self):
        assert Settings().MAGIC_LINK_RATE_LIMIT == "5/hour"

    def test_env_override_is_respected(self, monkeypatch):
        monkeypatch.setenv("MAGIC_LINK_RATE_LIMIT", "60/hour")
        assert Settings().MAGIC_LINK_RATE_LIMIT == "60/hour"

    def test_route_uses_the_setting_not_a_hardcoded_limit(self):
        source = Path("app/routers/v1/auth.py").read_text()
        anchor = source.index('@router.post("/magic-link")')
        window = source[anchor : anchor + 500]
        assert "settings.MAGIC_LINK_RATE_LIMIT" in window
        assert '@limiter.limit("5/hour")' not in window
