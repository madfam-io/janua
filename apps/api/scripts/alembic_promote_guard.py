#!/usr/bin/env python3
"""Refuse a promote that carries unacknowledged migrations.

WHY THIS IS A STATIC CHECK AND NOT A DATABASE QUERY. The natural design is
"read alembic_version from prod, compare to the repo's head, fail if behind".
promote-to-prod.yml cannot do that. It runs on a GitHub-hosted runner with no
route to the production database and no cluster credentials, and giving the
promote workflow a production database credential to make a nicer error message
is a straight trade of a real blast radius for a diagnostic — the promote job
already holds `contents: write`, so that credential would sit in the same job
that writes the prod manifest. Refused deliberately.

So the guard compares two things it CAN see, both in the repository:

  * `alembic heads` — the revision the code being promoted expects, derived by
    walking alembic/versions/ (parsed with `ast`, so this needs no database, no
    settings and no app import — same reason as test_alembic_revision_graph.py).
  * alembic/PROD_ALEMBIC_STATE.json:recorded_revision — the last value a human
    actually read out of production with `alembic_converge.py --check`.

If the head is ahead of the ledger by more than the allowed drift, the promote
stops unless the operator passes `migrations_acknowledged=true`.

WHAT THE GUARD ACTUALLY BUYS, stated honestly: it does not verify production.
It converts a silent assumption into a loud question. Today an operator can
promote code whose ORM selects a column the database does not have and find out
from 500s; janua is the ecosystem auth floor, so that is every downstream login.
After this, that promote requires someone to tick a box that says "I know there
are unapplied migrations". The check on the real database is
`alembic_converge.py --check` from inside the pod, which is the one place that
can reach it, and the runbook makes running it the precondition for ticking the
box.

FAIL-SAFE DIRECTION. A ledger nobody updates drifts toward "behind", which
demands the acknowledgement more often than strictly necessary. That is the
right way for it to be wrong.

Usage (from apps/api):

    python scripts/alembic_promote_guard.py                       # fail if drifted
    python scripts/alembic_promote_guard.py --acknowledged        # operator ticked the box
    python scripts/alembic_promote_guard.py --max-drift 0         # default
    python scripts/alembic_promote_guard.py --format github       # ::error:: annotations
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Optional

API_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = API_ROOT / "alembic" / "versions"
LEDGER_PATH = API_ROOT / "alembic" / "PROD_ALEMBIC_STATE.json"

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_ERROR = 2


def _literal(module: ast.Module, name: str):
    for node in module.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if node.value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                try:
                    return ast.literal_eval(node.value)
                except ValueError:
                    return None
    return None


def load_graph(versions_dir: Optional[Path] = None) -> dict:
    """revision id -> parent id (or None). Parsed, never imported."""
    graph = {}
    for path in sorted((versions_dir or VERSIONS_DIR).glob("*.py")):
        if path.name.startswith("__"):
            continue
        module = ast.parse(path.read_text(), filename=str(path))
        revision = _literal(module, "revision")
        if revision is None:
            continue
        graph[revision] = _literal(module, "down_revision")
    return graph


def linear_history(graph: dict) -> list:
    """Revisions oldest -> newest.

    Raises when the graph is not a single line. Janua's chain is linear and the
    revision-graph test enforces that it stays so; a branch here would make
    "how many revisions ahead" ambiguous, and guessing is worse than refusing.
    """
    if not graph:
        raise ValueError("no migrations found")

    children = {}
    for revision, parent in graph.items():
        children.setdefault(parent, []).append(revision)

    roots = children.get(None, [])
    if len(roots) != 1:
        raise ValueError(f"expected exactly one root revision, found {sorted(roots)}")

    order = []
    current = roots[0]
    while current is not None:
        order.append(current)
        nxt = children.get(current, [])
        if len(nxt) > 1:
            raise ValueError(f"revision {current} has multiple children: {sorted(nxt)}")
        current = nxt[0] if nxt else None

    if len(order) != len(graph):
        unreachable = sorted(set(graph) - set(order))
        raise ValueError(f"revisions unreachable from the root: {unreachable}")
    return order


def load_ledger(path: Optional[Path] = None) -> dict:
    """Read the ledger.

    The path is resolved at CALL time, not bound as a default argument: a
    default would freeze the module-level constant at import and make the
    module's own path unoverridable, which silently turns every test of this
    function into a test against the real repository file.
    """
    return json.loads((path or LEDGER_PATH).read_text())


def drift(order: list, recorded: Optional[str]) -> int:
    """How many revisions the repo head is ahead of `recorded`.

    An unrecognized (or absent) recorded revision counts as the whole chain:
    the honest reading of "production says something this repo has never heard
    of" is that we do not know what is applied, which is maximum drift.
    """
    if recorded not in order:
        return len(order)
    return len(order) - 1 - order.index(recorded)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alembic_promote_guard.py",
        description="Block a promote whose migrations production has not recorded.",
    )
    parser.add_argument(
        "--acknowledged",
        action="store_true",
        help="the operator passed migrations_acknowledged=true; warn instead of failing.",
    )
    parser.add_argument(
        "--max-drift",
        type=int,
        default=0,
        help="revisions the head may be ahead of the ledger before blocking (default 0).",
    )
    parser.add_argument(
        "--format",
        choices=("plain", "github"),
        default="plain",
        help="'github' emits ::error:: / ::warning:: annotations.",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)

    def emit(level: str, message: str) -> None:
        if args.format == "github":
            print(f"::{level}::{message}")
        else:
            print(
                f"{level.upper()}: {message}", file=sys.stderr if level == "error" else sys.stdout
            )

    try:
        order = linear_history(load_graph())
    except (OSError, ValueError) as exc:
        emit("error", f"could not read the migration chain: {exc}")
        return EXIT_ERROR

    head = order[-1]

    try:
        ledger = load_ledger()
    except (OSError, json.JSONDecodeError) as exc:
        emit("error", f"could not read {LEDGER_PATH.name}: {exc}")
        return EXIT_ERROR

    recorded = ledger.get("recorded_revision")
    verified_at = ledger.get("verified_at", "unknown")
    behind = drift(order, recorded)

    print(f"repo alembic head:        {head}")
    print(f"prod alembic_version:     {recorded} (ledger, verified {verified_at})")
    print(f"revisions ahead:          {behind} (allowed: {args.max_drift})")

    if behind <= args.max_drift:
        print("OK: production's recorded revision covers this promote.")
        return EXIT_OK

    unrecorded = order[order.index(recorded) + 1 :] if recorded in order else order
    message = (
        f"{behind} migration(s) are not recorded in production's alembic_version: "
        f"{', '.join(unrecorded)}. Promote does NOT run migrations."
    )

    if args.acknowledged:
        emit("warning", message + " Proceeding: migrations_acknowledged=true.")
        return EXIT_OK

    emit("error", message)
    emit(
        "error",
        "Verify the real database first: "
        "kubectl -n janua exec deploy/janua-api -- python scripts/alembic_converge.py --check. "
        "Then either converge (--stamp) and refresh alembic/PROD_ALEMBIC_STATE.json, or "
        "re-run this promote with migrations_acknowledged=true. "
        "See docs/runbooks/ALEMBIC_CONVERGENCE.md.",
    )
    return EXIT_BLOCKED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
