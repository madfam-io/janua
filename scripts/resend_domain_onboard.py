#!/usr/bin/env python3
"""Onboard a sending domain in Resend, and print the DNS it needs.

WHY A SCRIPT AND NOT THE DASHBOARD. The DNS records Resend requires are
generated per-domain (the DKIM public key is unique) so they cannot be written
into a runbook ahead of time — they have to be read back from the API at the
moment the domain is created. Transcribing them out of a dashboard by hand,
into `enclii providers cloudflare dns-apply` lines, is exactly where a DKIM key
loses a character and the domain silently never verifies. This prints the
records AND the dns-apply lines, from the API response.

It is idempotent: re-running against an existing domain finds it by name and
reports status rather than erroring or creating a duplicate.

WHAT IT DOES NOT DO. It does not touch DNS. Records are applied through Enclii
(`enclii providers cloudflare dns-apply`), per the repo's Enclii-first doctrine
— this script only tells you which ones. It also never prints the API key.

USAGE
    # 1. create (or find) the domain and print the DNS it needs
    RESEND_API_KEY=re_xxx python3 scripts/resend_domain_onboard.py creatumundo.mx

    # 2. after the records are applied via enclii, ask Resend to check them
    RESEND_API_KEY=re_xxx python3 scripts/resend_domain_onboard.py creatumundo.mx --verify

    # 3. poll status alone
    RESEND_API_KEY=re_xxx python3 scripts/resend_domain_onboard.py creatumundo.mx --status

Exit codes: 0 domain verified · 1 error · 2 domain exists but is not verified
(so CI or a wait-loop can branch on "not yet" without treating it as failure).

See docs/runbooks/resend-domain-onboarding.md for the full order of operations,
and docs/EMAIL_SENDER_POLICY.md for why the sender may not move until this
reports `verified`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

API_ROOT = "https://api.resend.com"

# Resend's default return-path subdomain. `POST /domains` accepts
# `custom_return_path` to change it; we keep the default so the records match
# every other MADFAM sending domain.
DEFAULT_REGION = "us-east-1"


def _api_key() -> str:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not key:
        sys.exit(
            "RESEND_API_KEY is not set.\n"
            "Export it from your operator environment (never commit it, never echo it):\n"
            "    export RESEND_API_KEY=...   # Resend dashboard -> API keys"
        )
    return key


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
    """One Resend API call. Never logs the key or the Authorization header."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            # api.resend.com sits behind Cloudflare, which rejects urllib's
            # default User-Agent with HTTP 403 "error code: 1010" before the
            # request reaches Resend (observed 2026-09-07 onboarding
            # creatumundo.mx). Any descriptive UA passes.
            "User-Agent": "janua-resend-domain-onboard/1.0 (+https://madfam.io)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        # The body may name the misconfiguration (bad key, duplicate domain);
        # it carries no secret, so it is safe to surface.
        sys.exit(f"Resend {method} {path} failed: HTTP {exc.code} {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"Resend {method} {path} unreachable: {exc.reason}")


def find_domain(name: str) -> Optional[Dict[str, Any]]:
    """The domain record for `name`, or None. Makes the script idempotent."""
    listed = _request("GET", "/domains")
    items = listed.get("data", listed) if isinstance(listed, dict) else listed
    for item in items or []:
        if str(item.get("name", "")).lower() == name.lower():
            return item
    return None


def create_domain(name: str, region: str) -> Dict[str, Any]:
    return _request("POST", "/domains", {"name": name, "region": region})


def get_domain(domain_id: str) -> Dict[str, Any]:
    return _request("GET", f"/domains/{domain_id}")


def verify_domain(domain_id: str) -> Dict[str, Any]:
    """Ask Resend to re-check DNS. Not instant — records must have propagated."""
    return _request("POST", f"/domains/{domain_id}/verify")


def _records(domain: Dict[str, Any]) -> List[Dict[str, Any]]:
    return domain.get("records") or []


def print_records(domain: Dict[str, Any]) -> None:
    """The DNS Resend wants, then the enclii lines that publish it."""
    records = _records(domain)
    if not records:
        print("  (no records returned — the domain may already be verified)")
        return

    print("\nDNS records Resend requires:")
    print(f"  {'TYPE':<6} {'NAME':<34} {'STATUS':<12} VALUE")
    for r in records:
        value = str(r.get("value", ""))
        shown = value if len(value) <= 60 else value[:57] + "..."
        print(
            f"  {str(r.get('type', '')):<6} {str(r.get('name', '')):<34} "
            f"{str(r.get('status', '')):<12} {shown}"
        )
        if r.get("priority") is not None:
            print(f"  {'':<6} {'':<34} {'':<12} (priority {r['priority']})")

    print("\nApply through Enclii (Enclii-first: do not edit DNS by hand):")
    for r in records:
        rtype = str(r.get("type", ""))
        name = str(r.get("name", ""))
        value = str(r.get("value", ""))
        priority = r.get("priority")
        # MX content carries the priority inline for the Cloudflare adapter.
        content = f"{priority} {value}" if rtype == "MX" and priority is not None else value
        print(
            f"  enclii providers cloudflare dns-apply {name} \\\n"
            f"    --type {rtype} --content '{content}' \\\n"
            f"    --proxied false --apply \\\n"
            f"    --reason 'Resend sending-domain verification for {domain.get('name')}'"
        )


def report(domain: Dict[str, Any]) -> int:
    status = str(domain.get("status", "unknown"))
    print(f"\nDomain : {domain.get('name')}")
    print(f"Id     : {domain.get('id')}")
    print(f"Region : {domain.get('region')}")
    print(f"Status : {status}")
    if status == "verified":
        print(
            "\nVERIFIED. Next step is the janua manifest, not this script:\n"
            f"  add '{domain.get('name')}' to RESEND_VERIFIED_DOMAINS\n"
            "  (comma-separated; keep madfam.io in the list)\n"
            "Until that env change is deployed, janua still sends the tenant's\n"
            "display name on the madfam.io address — by design."
        )
        return 0
    print(
        "\nNOT VERIFIED YET. Publish the records above, wait for propagation,\n"
        "then re-run with --verify. Do NOT add the domain to\n"
        "RESEND_VERIFIED_DOMAINS before this says verified: Resend rejects a\n"
        "send from an unverified domain, so the mail would not arrive at all."
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create/inspect a Resend sending domain and print its DNS.",
    )
    parser.add_argument("domain", help="the sending domain, e.g. creatumundo.mx")
    parser.add_argument(
        "--region", default=DEFAULT_REGION, help=f"Resend region (default {DEFAULT_REGION})"
    )
    parser.add_argument(
        "--verify", action="store_true", help="ask Resend to re-check DNS for this domain"
    )
    parser.add_argument(
        "--status", action="store_true", help="report status only; never create"
    )
    args = parser.parse_args()

    name = args.domain.strip().lower().lstrip("@")

    existing = find_domain(name)

    if existing is None:
        if args.status or args.verify:
            sys.exit(
                f"Domain {name} is not registered in Resend. "
                "Run without --status/--verify first to create it."
            )
        print(f"Creating {name} in Resend ({args.region})...")
        domain = create_domain(name, args.region)
    else:
        print(f"Domain {name} already exists in Resend (idempotent re-run).")
        # The list endpoint omits `records`; fetch the full record for DNS.
        domain = get_domain(str(existing.get("id")))

    if args.verify:
        print("Asking Resend to re-check DNS...")
        verify_domain(str(domain.get("id")))
        domain = get_domain(str(domain.get("id")))

    if not args.status:
        print_records(domain)

    return report(domain)


if __name__ == "__main__":
    sys.exit(main())
