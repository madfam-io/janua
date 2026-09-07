#!/usr/bin/env python3
"""Move a tenant onto their OWN provider account — and back.

Owner directive, 2026-09-06: «we should allow mechanisms so that CTM and any
other vCTO client can easily move to their own Resend (or preferred provider)
account.» This is that mechanism.

WHAT "MOVING" ACTUALLY IS. A tenant's sending identity is a `SenderBinding`
(`apps/api/app/services/sender_binding.py`): display name, address, reply-to,
provider, ACCOUNT, credential reference, verified domains. Moving a client to
their own Resend account changes exactly two of those fields —
`account: madfam -> tenant` and `credential_ref` — plus `verified_domains`,
because domain verification in Resend is per-ACCOUNT and the global
`RESEND_VERIFIED_DOMAINS` describes MADFAM's account, not theirs.

No code path changes. No caller changes. No template changes. That separation
is the point: portability is a binding edit, not a migration.

THE ORDER MATTERS AND IT IS NOT NEGOTIABLE

    1. verify   the domain exists and is VERIFIED in the TENANT's account
    2. dns      print the records that still need to move, if any
    3. switch   flip the binding (only after 1 reports verified)
    4. rollback one command, any time

Doing 3 before 1 sends every message for that tenant on an account that has
not verified their domain, and Resend REJECTS such a send — the sign-in link
does not arrive at all. So `switch` refuses to run until `verify` passes,
unless you pass --force (which prints what you are overriding).

CREDENTIALS: THIS SCRIPT NEVER SEES ONE ON THE COMMAND LINE.
The tenant's API key is read from the environment for the API calls
(TENANT_RESEND_API_KEY) and is written to Vault by the OPERATOR, out of band.
The binding stores only a REFERENCE. Nothing here prints, logs, echoes or
stores a key, and `--check-credential` answers "is it in Vault?" with a boolean
rather than a value.

OPERATOR ONE-SHOT (the whole migration)

    # 0. Aldo pastes the tenant's key once, silently, into the operator shell:
    read -rs TENANT_RESEND_API_KEY && export TENANT_RESEND_API_KEY
    #    ...and into Vault, at the path the binding will reference:
    vault kv put secret/janua/senders/ctm resend_api_key="$TENANT_RESEND_API_KEY"

    # 1. does the tenant's own account have the domain, verified?
    python3 scripts/sender_binding_switch.py ctm --verify

    # 2. if not: create it there and print the DNS to move
    python3 scripts/sender_binding_switch.py ctm --onboard

    # 3. once step 1 says verified, flip the binding
    python3 scripts/sender_binding_switch.py ctm --switch \\
        --credential-ref 'secret/data/janua/senders/ctm#resend_api_key'

    # 4. if anything looks wrong
    python3 scripts/sender_binding_switch.py ctm --rollback

Steps 3 and 4 EDIT `sender_binding.py` in place and print a diff. They are a
code change by design — a binding is versioned configuration, so a switch is
reviewable in a PR and revertible with git, rather than a live mutation nobody
can archaeology later.

Exit codes: 0 ok · 1 error · 2 not verified yet (so a wait-loop can branch).

See docs/runbooks/resend-domain-onboarding.md ("Migrar a tu propia cuenta") and
docs/EMAIL_SENDER_POLICY.md.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

API_ROOT = "https://api.resend.com"
DEFAULT_REGION = "us-east-1"

REPO_ROOT = Path(__file__).resolve().parent.parent
BINDING_MODULE = REPO_ROOT / "apps" / "api" / "app" / "services" / "sender_binding.py"

#: The env var holding the TENANT's Resend key for the API calls this script
#: makes. Deliberately NOT `RESEND_API_KEY`: that one is MADFAM's, and reusing
#: it is exactly how you would "verify" a domain on the wrong account and then
#: switch to an account that cannot send.
TENANT_KEY_ENV = "TENANT_RESEND_API_KEY"


# ==========================================================================
# Resend API — the TENANT's account
# ==========================================================================
def _tenant_api_key() -> str:
    key = os.environ.get(TENANT_KEY_ENV, "").strip()
    if not key:
        sys.exit(
            f"{TENANT_KEY_ENV} is not set.\n"
            "This must be the TENANT's own Resend API key, not MADFAM's.\n"
            "Read it in without echoing it to the terminal or to history:\n"
            f"    read -rs {TENANT_KEY_ENV} && export {TENANT_KEY_ENV}"
        )
    return key


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
    """One Resend API call on the TENANT's account. Never logs the key."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_tenant_api_key()}",
            "Content-Type": "application/json",
            # api.resend.com sits behind Cloudflare, which rejects urllib's
            # default User-Agent with HTTP 403 "error code: 1010" before the
            # request reaches Resend (observed 2026-09-07 onboarding
            # creatumundo.mx; fixed for the sibling script in #606). Any
            # descriptive UA passes. Without it EVERY call here fails --
            # including the --verify gate that --switch refuses to run without,
            # so the whole migration path is blocked by a 403 that looks like
            # a bad API key.
            "User-Agent": "janua-sender-binding-switch/1.0 (+https://madfam.io)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        sys.exit(f"Resend {method} {path} failed: HTTP {exc.code} {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"Resend {method} {path} unreachable: {exc.reason}")


def find_domain(name: str) -> Optional[Dict[str, Any]]:
    listed = _request("GET", "/domains")
    items = listed.get("data", listed) if isinstance(listed, dict) else listed
    for item in items or []:
        if str(item.get("name", "")).lower() == name.lower():
            return item
    return None


def print_dns(domain: Dict[str, Any]) -> None:
    """The DNS the TENANT's account requires, and the enclii lines for it.

    Same shape as scripts/resend_domain_onboard.py, deliberately: an operator
    who has done the MADFAM-account onboarding should recognise this output
    exactly. The VALUES differ — the DKIM key is per-account as well as
    per-domain, which is the whole reason moving accounts needs new records.
    """
    records = domain.get("records") or []
    if not records:
        print("  (no records returned — the domain may already be verified)")
        return
    print("\nDNS records the TENANT's Resend account requires:")
    print(f"  {'TYPE':<6} {'NAME':<34} {'STATUS':<12} VALUE")
    for r in records:
        value = str(r.get("value", ""))
        shown = value if len(value) <= 60 else value[:57] + "..."
        print(
            f"  {str(r.get('type', '')):<6} {str(r.get('name', '')):<34} "
            f"{str(r.get('status', '')):<12} {shown}"
        )
    print("\nApply through Enclii (Enclii-first: do not edit DNS by hand):")
    for r in records:
        rtype = str(r.get("type", ""))
        name = str(r.get("name", ""))
        value = str(r.get("value", ""))
        priority = r.get("priority")
        content = f"{priority} {value}" if rtype == "MX" and priority is not None else value
        print(
            f"  enclii providers cloudflare dns-apply {name} \\\n"
            f"    --type {rtype} --content '{content}' \\\n"
            f"    --proxied false --apply \\\n"
            f"    --reason 'Resend verification for {domain.get('name')} on tenant account'"
        )


# ==========================================================================
# The binding file — read and edit
# ==========================================================================
def _binding_source() -> str:
    if not BINDING_MODULE.exists():
        sys.exit(f"binding module not found: {BINDING_MODULE}")
    return BINDING_MODULE.read_text()


def _binding_block(source: str, tenant: str) -> tuple[int, int]:
    """The (start, end) character offsets of one tenant's binding literal.

    Located by the `tenant="<key>"` line inside a `SenderBinding(` call, then
    matched to its closing paren by depth. Parsing rather than regexing the
    whole record keeps this honest when a field is added.
    """
    marker = f'tenant="{tenant}"'

    # EVERY occurrence, not the first. The module docstring shows a worked
    # SenderBinding(...) example carrying the same `tenant="ctm"` line, and
    # taking the first hit would edit the documentation instead of the record.
    # A real binding is one assigned to a module-level NAME, so that is the
    # discriminator.
    for match in re.finditer(re.escape(marker), source):
        start = source.rfind("SenderBinding(", 0, match.start())
        if start == -1:
            continue
        line_start = source.rfind("\n", 0, start) + 1
        prefix = source[line_start:start]
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*$", prefix):
            continue  # the docstring example, or a nested call
        depth = 0
        for pos in range(start, len(source)):
            if source[pos] == "(":
                depth += 1
            elif source[pos] == ")":
                depth -= 1
                if depth == 0:
                    return start, pos + 1
        sys.exit(f"unterminated binding for tenant {tenant!r}")
    sys.exit(f"no binding for tenant {tenant!r} in {BINDING_MODULE.name}")


def _set_field(block: str, field: str, literal: str) -> str:
    """Replace one `field=<value>,` assignment inside a binding literal.

    Line-anchored deliberately: the fields in these records are interleaved
    with explanatory comments, and a pattern allowed to span newlines would
    swallow the comment blocks between them.
    """
    pattern = re.compile(rf"^(\s*){field}=[^\n]*,\s*$", re.MULTILINE)
    if not pattern.search(block):
        sys.exit(f"field {field!r} not found in the binding literal")
    return pattern.sub(lambda m: f"{m.group(1)}{field}={literal},", block, count=1)


def _show_diff(before: str, after: str) -> None:
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{BINDING_MODULE.name}",
        tofile=f"b/{BINDING_MODULE.name}",
    )
    sys.stdout.writelines(diff)


def _write(source: str, after: str, dry_run: bool) -> None:
    _show_diff(source, after)
    if dry_run:
        print("\n--dry-run: nothing written.")
        return
    BINDING_MODULE.write_text(after)
    print(f"\nWrote {BINDING_MODULE}")
    print(
        "This is a CODE change: commit it on a branch and open a PR.\n"
        "The binding is versioned configuration — that is what makes the switch\n"
        "reviewable and `git revert`-able."
    )


def do_switch(
    tenant: str, domain: str, credential_ref: str, verified: List[str], dry_run: bool
) -> int:
    source = _binding_source()
    start, end = _binding_block(source, tenant)
    block = source[start:end]

    if not credential_ref:
        sys.exit(
            "--credential-ref is required for --switch.\n"
            "It is a NAME, never a key. A Vault path, e.g.\n"
            f"    secret/data/janua/senders/{tenant}#resend_api_key"
        )
    if credential_ref == "RESEND_API_KEY":
        sys.exit(
            "--credential-ref points at MADFAM's own key. A tenant-account\n"
            "binding referencing MADFAM's credential would send the tenant's\n"
            "mail on MADFAM's account while claiming otherwise; the binding\n"
            "registry rejects it at import."
        )

    verified_literal = "(" + ", ".join(f'"{d}"' for d in verified) + ("," if verified else "") + ")"
    updated = block
    updated = _set_field(updated, "account", "ACCOUNT_TENANT")
    updated = _set_field(updated, "credential_ref", f'"{credential_ref}"')
    updated = _set_field(updated, "verified_domains", verified_literal)

    _write(source, source[:start] + updated + source[end:], dry_run)
    print(
        f"\nTenant {tenant!r} now sends on its OWN account.\n"
        f"  provider account : tenant\n"
        f"  credential_ref   : {credential_ref}   (a reference; the value lives in Vault)\n"
        f"  verified domains : {', '.join(verified) or '(none!)'}\n"
        "\nBefore deploying, confirm the credential is actually in Vault:\n"
        f"  python3 scripts/sender_binding_switch.py {tenant} --check-credential"
    )
    return 0


def do_rollback(tenant: str, dry_run: bool) -> int:
    source = _binding_source()
    start, end = _binding_block(source, tenant)
    block = source[start:end]

    updated = block
    updated = _set_field(updated, "account", "ACCOUNT_MADFAM")
    updated = _set_field(updated, "credential_ref", "MADFAM_RESEND_CREDENTIAL_REF")
    # Back to empty: on MADFAM's account the global RESEND_VERIFIED_DOMAINS is
    # the authority, and a stale per-binding list would silently outrank it.
    updated = _set_field(updated, "verified_domains", "()")

    _write(source, source[:start] + updated + source[end:], dry_run)
    print(
        f"\nTenant {tenant!r} is back on MADFAM's account.\n"
        "The From line is unchanged; only the account that carries it moved.\n"
        "Confirm the domain is still in RESEND_VERIFIED_DOMAINS for MADFAM's\n"
        "account, or the address will downgrade to hola@madfam.io."
    )
    return 0


def do_check_credential(tenant: str) -> int:
    """Answer 'is the credential in place?' as a boolean. Never prints a value."""
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
    try:
        import asyncio

        from app.services.sender_binding import resolve_binding
        from app.services.sender_credentials import has_credential
    except ImportError as exc:
        sys.exit(f"cannot import the binding modules (run from the repo root): {exc}")

    binding = resolve_binding(tenant)
    present = asyncio.run(has_credential(binding))
    print(f"tenant           : {binding.tenant}")
    print(f"account          : {binding.account}")
    print(f"credential_ref   : {binding.credential_ref}")
    print(f"credential found : {'YES' if present else 'NO'}")
    if not present:
        print(
            "\nThe reference does not resolve. Check VAULT_ADDR/VAULT_TOKEN are\n"
            "exported and that the path and field exist. Never echo the value."
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move a tenant onto their own provider account, or back.",
    )
    parser.add_argument("tenant", help="tenant key, e.g. ctm")
    parser.add_argument("--domain", help="sending domain (default: the binding's own)")
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument(
        "--onboard",
        action="store_true",
        help="create the domain in the TENANT's Resend account and print its DNS",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="ask the TENANT's account to re-check DNS, then report status",
    )
    parser.add_argument(
        "--switch", action="store_true", help="flip the binding onto the tenant's account"
    )
    parser.add_argument(
        "--rollback", action="store_true", help="flip the binding back to MADFAM's account"
    )
    parser.add_argument(
        "--check-credential",
        action="store_true",
        help="report whether the binding's credential_ref resolves (never prints it)",
    )
    parser.add_argument("--credential-ref", default="", help="Vault path or env name (a NAME)")
    parser.add_argument(
        "--force", action="store_true", help="allow --switch before the domain reports verified"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")
    args = parser.parse_args()

    tenant = args.tenant.strip().lower()

    if args.check_credential:
        return do_check_credential(tenant)

    if args.rollback:
        return do_rollback(tenant, args.dry_run)

    # Everything below talks to the tenant's Resend account, so it needs the
    # sending domain. Default it from the binding rather than making the
    # operator retype it.
    domain = (args.domain or "").strip().lower()
    if not domain:
        source = _binding_source()
        start, end = _binding_block(source, tenant)
        match = re.search(r'from_address="[^@"]+@([^"]+)"', source[start:end])
        if not match:
            sys.exit("could not read the binding's domain; pass --domain")
        domain = match.group(1).lower()

    if args.onboard or args.verify:
        existing = find_domain(domain)
        if existing is None:
            if args.verify:
                sys.exit(
                    f"{domain} is not registered in the TENANT's Resend account. "
                    "Run with --onboard first."
                )
            print(f"Creating {domain} in the TENANT's Resend account ({args.region})...")
            record = _request("POST", "/domains", {"name": domain, "region": args.region})
        else:
            print(f"{domain} already exists in the TENANT's account (idempotent re-run).")
            record = _request("GET", f"/domains/{existing.get('id')}")

        if args.verify:
            print("Asking Resend to re-check DNS...")
            _request("POST", f"/domains/{record.get('id')}/verify")
            record = _request("GET", f"/domains/{record.get('id')}")

        status = str(record.get("status", "unknown"))
        print(f"\nDomain : {record.get('name')}")
        print(f"Status : {status}   (on the TENANT's account)")
        if status != "verified":
            print_dns(record)
            print(
                "\nNOT VERIFIED YET on the tenant's account. Publish the records\n"
                "above through Enclii, wait for propagation, then re-run --verify.\n"
                "Do NOT --switch before this says verified: Resend rejects a send\n"
                "from an unverified domain, so the mail would not arrive at all."
            )
            return 2
        print("\nVERIFIED on the tenant's account. Safe to --switch.")
        return 0

    if args.switch:
        if not args.force:
            existing = find_domain(domain)
            status = str((existing or {}).get("status", "missing"))
            if status != "verified":
                print(
                    f"REFUSING to switch: {domain} is '{status}' on the tenant's\n"
                    "account, not 'verified'. Switching now would send every message\n"
                    "for this tenant on an account that will reject it — the sign-in\n"
                    "links would not arrive at all.\n"
                    "Run --onboard / --verify first, or --force if you know better."
                )
                return 2
        return do_switch(tenant, domain, args.credential_ref.strip(), [domain], args.dry_run)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
