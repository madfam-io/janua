"""The operator scripts that talk to api.resend.com must send a User-Agent.

WHY THIS TEST EXISTS. api.resend.com sits behind Cloudflare, and Cloudflare
rejects urllib's default User-Agent ("Python-urllib/3.x") with HTTP 403 and a
body of `error code: 1010` -- before the request ever reaches Resend. Observed
2026-09-07 while onboarding creatumundo.mx. The failure is nasty because of how
it PRESENTS: a 403 on an authenticated endpoint reads as "bad API key", so the
operator goes looking at the credential instead of the transport, with a client
waiting on a sign-in link.

`scripts/resend_domain_onboard.py` was fixed in #606. Its sibling
`scripts/sender_binding_switch.py` carried the same defect until this change --
and there it is worse than an inconvenience: EVERY tenant-account call goes
through `_request`, including the `--verify` gate that `--switch` refuses to
run without, so the whole "move a client to their own Resend account" path is
blocked by a 403 that looks like a credential problem.

WHAT IS ASSERTED, and why this shape. The scripts are checked by PARSING them
with `ast` rather than importing and calling them: importing is fine, but
exercising `_request` for real would mean either a network call or mocking
urllib deeply enough that the test proves the mock rather than the header. The
header is a static literal in a static dict, so reading it out of the source is
both the strongest and the least brittle assertion available -- the same
parse-don't-import reasoning as tests/unit/test_alembic_converge.py's drift
half.

The guard is written over a LIST of scripts, so a third Resend-touching script
added later is one line away from being covered instead of silently uncovered.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# apps/api/tests/unit/ -> apps/api -> apps -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]

#: Every operator script that calls api.resend.com through urllib. Add new ones
#: here; the assertions below then apply to them automatically.
RESEND_SCRIPTS = (
    "scripts/resend_domain_onboard.py",
    "scripts/sender_binding_switch.py",
)

#: Cloudflare's rejection is of the DEFAULT agent, so any descriptive value
#: passes. We require the script to identify itself as janua rather than
#: pinning an exact string: the point is "not urllib's default", not a
#: particular version number nobody would remember to update.
REQUIRED_UA_PREFIX = "janua-"


def _request_headers(path: Path) -> dict[str, str]:
    """The literal `headers={...}` dict passed to urllib.request.Request.

    Returns only the entries whose key AND value are plain string literals --
    which is exactly the set this test reasons about. `Authorization` is an
    f-string and therefore absent by construction, which is a happy accident:
    nothing in this test can ever read a credential.
    """
    tree = ast.parse(path.read_text(), filename=str(path))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # urllib.request.Request(...)
        if not (isinstance(func, ast.Attribute) and func.attr == "Request"):
            continue
        for keyword in node.keywords:
            if keyword.arg != "headers" or not isinstance(keyword.value, ast.Dict):
                continue
            headers: dict[str, str] = {}
            for key, value in zip(keyword.value.keys, keyword.value.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    headers[key.value] = value.value
            return headers

    pytest.fail(f"{path}: no urllib.request.Request(headers={{...}}) call found")


@pytest.mark.parametrize("script", RESEND_SCRIPTS)
def test_resend_script_sends_a_user_agent(script: str) -> None:
    """Without this header Cloudflare answers 403 'error code: 1010'."""
    path = REPO_ROOT / script
    assert path.exists(), f"{script} not found at {path}"

    headers = _request_headers(path)

    assert "User-Agent" in headers, (
        f"{script} calls api.resend.com without a User-Agent. Cloudflare "
        "rejects urllib's default with HTTP 403 'error code: 1010', which "
        "presents as an authentication failure. Add a descriptive UA."
    )
    assert headers["User-Agent"].startswith(REQUIRED_UA_PREFIX), (
        f"{script} sends User-Agent {headers['User-Agent']!r}; it should "
        f"identify itself as janua (prefix {REQUIRED_UA_PREFIX!r}) so a "
        "Resend-side or Cloudflare-side log names the caller."
    )


@pytest.mark.parametrize("script", RESEND_SCRIPTS)
def test_resend_script_still_sends_json(script: str) -> None:
    """The UA addition must not have displaced the existing headers."""
    headers = _request_headers(REPO_ROOT / script)
    assert headers.get("Content-Type") == "application/json"
