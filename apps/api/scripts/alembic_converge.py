#!/usr/bin/env python3
"""Reconcile `alembic_version` with migrations that were applied BY HAND.

THE STATE THIS EXISTS FOR (measured against production 2026-09-03):

    alembic_version.version_num = '011_invitation_columns'

...while the schema already carries everything 012, 013, 015 and 016 create,
because each was applied by hand, and 014 (`capability_links`) is applied by
the operator's bootstrap SQL — deliberately, without touching the version
table. `promote-to-prod.yml` runs NO migrations in this ecosystem, so the
version row is not a lie anyone told: it is what happens when the only thing
that ever writes it never runs.

WHY THAT IS DANGEROUS RATHER THAN MERELY UNTIDY. The version row is alembic's
ONLY input when deciding what to do next. Read as written, it says 012 onwards
have not happened, so `alembic upgrade head` would replay all five. The
migrations from 012 on are re-entrant on purpose (each checks `inspect()`
before creating), which is exactly why nobody has been burned yet — but that
guard is a property of five particular files, not of the repository, and 014's
own docstring records the failure mode it is defending against:
DuplicateTable, which aborts the WHOLE chain and pins the database at its
parent revision. The moment one migration is written without the guard, the
stale version row turns a routine upgrade into an outage. Convergence is what
takes that loaded gun off the table.

WHY `stamp` AND NEVER `upgrade`. `upgrade` runs DDL. Against a schema that
already has the objects, the best case is that the re-entrancy guards make it a
no-op and the worst case is a failed transaction — and neither is worth finding
out on production. `stamp` writes one row and touches no other object: it tells
alembic "this revision is already true", which is precisely the fact we have
verified independently by looking at the schema. So this script's whole job is
to earn the right to say that, by proving every object of a revision is present
before stamping it.

WHY PARTIAL IS A HARD STOP. If a revision created three objects and only two
are present, the schema is in a state no migration produces. Stamping it would
record a lie and permanently hide the missing object from every future upgrade
(alembic would never revisit that revision), and upgrading past it is this
script's forbidden operation. Both directions are wrong, so it refuses to do
anything at all and exits non-zero: a human must look.

USAGE (read-only by default — `--check` and no flag are the same thing):

    python scripts/alembic_converge.py --check
    python scripts/alembic_converge.py --stamp          # writes alembic_version
    python scripts/alembic_converge.py --stamp --yes    # no confirmation prompt

The database URL is read from the environment (`DIRECT_DATABASE_URL`, else
`DATABASE_URL`), the same precedence alembic/env.py uses, and is NEVER printed:
every diagnostic names the host and database only, so this is safe to run with
the output pasted into a ticket.

See docs/runbooks/ALEMBIC_CONVERGENCE.md for the operator procedure.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

API_ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
# What each revision creates.
#
# Derived by reading apps/api/alembic/versions/. Kept here as data rather than
# by importing the migration modules for the same reason
# tests/unit/test_alembic_revision_graph.py parses with `ast`: this must work
# in an environment where the app package may not import at all. The pairing is
# not left to trust — tests/unit/test_alembic_converge.py re-derives these
# names from the migration sources and fails when the two drift apart.
#
# Only 012+ appear. Everything up to 011 is what production's version row
# already claims, so those revisions are not in question; this table covers
# exactly the hand-applied span.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Expectation:
    """One schema object a revision creates, and how to look for it."""

    kind: str  # "table" | "column" | "index"
    table: str
    name: Optional[str] = None  # column or index name; None for a table

    def describe(self) -> str:
        if self.kind == "table":
            return f"table {self.table}"
        if self.kind == "column":
            return f"column {self.table}.{self.name}"
        return f"index {self.name} on {self.table}"


@dataclass(frozen=True)
class Revision:
    revision: str
    summary: str
    expects: tuple[Expectation, ...] = field(default_factory=tuple)


# Ordered oldest -> newest. The order IS the stamp order.
REVISIONS: tuple[Revision, ...] = (
    Revision(
        revision="012_user_spanish_formality",
        summary="users.spanish_formality (tú/usted register)",
        expects=(Expectation("column", "users", "spanish_formality"),),
    ),
    Revision(
        revision="013_per_tenant_email_uniqueness",
        summary="per-tenant email uniqueness (two partial unique indexes)",
        expects=(
            Expectation("index", "users", "uq_users_tenant_email"),
            Expectation("index", "users", "uq_users_email_global"),
        ),
    ),
    Revision(
        revision="014_capability_links",
        summary="capability_links table + 3 indexes",
        expects=(
            Expectation("table", "capability_links"),
            Expectation("index", "capability_links", "uq_capability_links_token_hash"),
            Expectation("index", "capability_links", "ix_capability_links_tenant_id"),
            Expectation("index", "capability_links", "ix_capability_links_tenant_subject"),
        ),
    ),
    Revision(
        revision="015_user_is_service_acct",
        summary="users.is_service_account",
        expects=(Expectation("column", "users", "is_service_account"),),
    ),
    Revision(
        revision="016_org_member_app_roles",
        summary="organization_member_app_roles table + 2 indexes",
        expects=(
            Expectation("table", "organization_member_app_roles"),
            Expectation("index", "organization_member_app_roles", "ix_org_member_app_roles_member"),
            Expectation("index", "organization_member_app_roles", "uq_org_member_app_roles_live"),
        ),
    ),
)

# 013 additionally DROPS ix_users_email once its two replacements exist. That
# drop is deliberately NOT an expectation: an environment built by
# `Base.metadata.create_all` carries ix_users_email alongside the new indexes,
# and refusing to stamp there would block precisely the environments this
# script exists to converge. Presence of the two new indexes is what proves 013
# ran; the leftover old index is cosmetic and reported as a note, not a gap.
LEGACY_GLOBAL_EMAIL_INDEX = "ix_users_email"


# --------------------------------------------------------------------------
# Result model
# --------------------------------------------------------------------------


@dataclass
class RevisionStatus:
    revision: Revision
    present: list[Expectation]
    missing: list[Expectation]

    @property
    def is_complete(self) -> bool:
        return not self.missing

    @property
    def is_absent(self) -> bool:
        return not self.present

    @property
    def is_partial(self) -> bool:
        return bool(self.present) and bool(self.missing)

    @property
    def verdict(self) -> str:
        if self.is_complete:
            return "PRESENTE"
        if self.is_absent:
            return "AUSENTE"
        return "PARCIAL"


class SchemaProbe:
    """Answers "does this object exist?" against a live schema.

    Wraps a SQLAlchemy inspector, but every lookup is memoized per table so a
    run makes a handful of catalog queries rather than one per expectation.
    """

    def __init__(self, inspector) -> None:
        self._inspector = inspector
        self._tables: Optional[set] = None
        self._columns: dict = {}
        self._indexes: dict = {}

    def tables(self) -> set:
        if self._tables is None:
            self._tables = set(self._inspector.get_table_names())
        return self._tables

    def columns(self, table: str) -> set:
        if table not in self._columns:
            if table not in self.tables():
                self._columns[table] = set()
            else:
                self._columns[table] = {c["name"] for c in self._inspector.get_columns(table)}
        return self._columns[table]

    def indexes(self, table: str) -> set:
        if table not in self._indexes:
            if table not in self.tables():
                self._indexes[table] = set()
            else:
                names = {ix["name"] for ix in self._inspector.get_indexes(table)}
                # A UNIQUE CONSTRAINT and a UNIQUE INDEX are different catalog
                # objects in Postgres and get_indexes() does not always report
                # the former. `op.create_index(unique=True)` makes an index, so
                # this normally does not matter -- but a schema built from the
                # ORM may carry the constraint form of the same name, and
                # missing it would report a false gap and block convergence.
                try:
                    names |= {
                        uc["name"]
                        for uc in self._inspector.get_unique_constraints(table)
                        if uc.get("name")
                    }
                except NotImplementedError:  # pragma: no cover - dialect-dependent
                    pass
                self._indexes[table] = names
        return self._indexes[table]

    def has(self, expectation: Expectation) -> bool:
        if expectation.kind == "table":
            return expectation.table in self.tables()
        if expectation.kind == "column":
            return expectation.name in self.columns(expectation.table)
        if expectation.kind == "index":
            return expectation.name in self.indexes(expectation.table)
        raise ValueError(f"unknown expectation kind {expectation.kind!r}")


def inspect_revisions(probe: SchemaProbe, revisions=REVISIONS) -> list[RevisionStatus]:
    """Classify every revision as PRESENTE / PARCIAL / AUSENTE."""
    statuses = []
    for revision in revisions:
        present, missing = [], []
        for expectation in revision.expects:
            (present if probe.has(expectation) else missing).append(expectation)
        statuses.append(RevisionStatus(revision=revision, present=present, missing=missing))
    return statuses


def highest_stampable(statuses: list[RevisionStatus]) -> Optional[str]:
    """The newest revision whose objects — and every earlier one's — are ALL present.

    A prefix, deliberately. Revisions are a chain: stamping 016 asserts 012-015
    are true too, because alembic records one version and infers the rest of the
    history from it. So a gap anywhere stops the walk, even if later revisions
    happen to be complete.
    """
    stampable = None
    for status in statuses:
        if not status.is_complete:
            break
        stampable = status.revision.revision
    return stampable


def find_partial(statuses: list[RevisionStatus]) -> list[RevisionStatus]:
    return [s for s in statuses if s.is_partial]


# --------------------------------------------------------------------------
# Database access
# --------------------------------------------------------------------------


def resolve_database_url() -> str:
    """Same precedence as alembic/env.py: DIRECT_DATABASE_URL wins.

    When the runtime routes through pgbouncer, DIRECT_DATABASE_URL is the
    connection that can actually run DDL/DDL-adjacent work; env.py prefers it
    for exactly that reason, and disagreeing here would mean inspecting one
    database and stamping another.
    """
    url = os.environ.get("DIRECT_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
    if not url:
        raise SystemExit(
            "No database URL. Set DATABASE_URL (or DIRECT_DATABASE_URL) in the "
            "environment. It is read, never printed, and never passed on argv."
        )
    return url


def to_sync_url(url: str) -> str:
    """Strip async drivers: this script uses a plain synchronous inspector."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "sqlite+aiosqlite://", "sqlite://"
    )


def redact(url: str) -> str:
    """host/database only — credentials never reach stdout, a log or a ticket."""
    try:
        parts = urlsplit(to_sync_url(url))
        database = (parts.path or "").lstrip("/") or "?"
        if not parts.hostname:
            # sqlite and other file/host-less URLs: the path IS the database.
            return database
        port = f":{parts.port}" if parts.port else ""
        return f"{parts.hostname}{port}/{database}"
    except ValueError:  # pragma: no cover - malformed URL
        return "<unparseable url>"


def read_alembic_version(connection) -> Optional[str]:
    """The recorded revision, or None when the table does not exist / is empty."""
    from sqlalchemy import text

    try:
        row = connection.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    except Exception:
        return None
    return row[0] if row else None


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def render_table(statuses: list[RevisionStatus]) -> str:
    """The `revision | expected objects | present?` table, one line per object."""
    rows = [("revision", "objeto esperado", "¿presente?")]
    for status in statuses:
        first = True
        for expectation in status.revision.expects:
            present = expectation in status.present
            rows.append(
                (
                    status.revision.revision if first else "",
                    expectation.describe(),
                    "sí" if present else "NO",
                )
            )
            first = False
        rows.append(("", f"  -> {status.verdict}", ""))

    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    lines = []
    for index, row in enumerate(rows):
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(3)).rstrip())
        if index == 0:
            lines.append("  ".join("-" * widths[i] for i in range(3)))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Stamping
# --------------------------------------------------------------------------


def stamp(revision: str, url: str) -> subprocess.CompletedProcess:
    """`alembic stamp <rev>` in a subprocess.

    A subprocess because alembic/env.py resolves its URL from `settings` at
    import time: only a fresh process picks up the URL we resolved here, and
    an in-process call would silently target whatever the ambient settings say.
    Both URL variables are set so env.py's own preference cannot pick a
    different database than the one just inspected.
    """
    return subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", revision],
        cwd=str(API_ROOT),
        env={**os.environ, "DATABASE_URL": url, "DIRECT_DATABASE_URL": url},
        capture_output=True,
        text=True,
        timeout=120,
    )


def stamp_path(statuses: list[RevisionStatus], current: Optional[str], target: str) -> list[str]:
    """The revisions to stamp, in order, to move `current` up to `target`.

    Step by step rather than one jump to the target, so that a failure halfway
    leaves the version row at a revision that is still true, and so the audit
    trail shows each assertion separately. Anything at or below `current` is
    skipped: it is already recorded.
    """
    ordered = [s.revision.revision for s in statuses]
    if target not in ordered:  # pragma: no cover - defensive
        return []
    path = ordered[: ordered.index(target) + 1]
    if current in ordered:
        path = path[ordered.index(current) + 1 :]
    return path


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_BEHIND = 2
EXIT_ERROR = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alembic_converge.py",
        description=(
            "Compare the live schema against migrations 012-016 and, with --stamp, "
            "record the revisions that are provably already applied. Never upgrades."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="read-only report (default). Exit 2 when the version row is behind the schema.",
    )
    mode.add_argument(
        "--stamp",
        action="store_true",
        help="write alembic_version up to the highest fully-present revision.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the interactive confirmation before stamping.",
    )
    parser.add_argument(
        "--max-drift",
        type=int,
        default=0,
        help=(
            "with --check, tolerate up to N unrecorded-but-present revisions before "
            "exiting non-zero. Default 0: any drift is reported as drift."
        ),
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        from sqlalchemy import create_engine
        from sqlalchemy import inspect as sa_inspect
    except ImportError:  # pragma: no cover - dependency is in requirements.txt
        print("SQLAlchemy no está instalado en este entorno.", file=sys.stderr)
        return EXIT_ERROR

    url = resolve_database_url()
    sync_url = to_sync_url(url)
    print(f"Base de datos: {redact(url)}")

    try:
        engine = create_engine(sync_url)
        with engine.connect() as connection:
            recorded = read_alembic_version(connection)
            probe = SchemaProbe(sa_inspect(connection))
            statuses = inspect_revisions(probe)
            legacy_index_present = LEGACY_GLOBAL_EMAIL_INDEX in probe.indexes("users")
    except Exception as exc:  # noqa: BLE001 - any driver error is a clean refusal here
        # Only the exception TYPE is shown. Several drivers put the full DSN --
        # password included -- into str(exc), and this output is meant to be
        # pasteable into a ticket.
        print(
            f"No se pudo inspeccionar el esquema ({type(exc).__name__}). "
            "Revisa la conectividad y las credenciales.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    print(f"alembic_version registrado: {recorded or '(sin fila / sin tabla)'}")
    print()
    print(render_table(statuses))
    print()

    if legacy_index_present:
        print(
            f"Nota: el índice heredado {LEGACY_GLOBAL_EMAIL_INDEX} sigue presente. "
            "013 lo elimina al final; su presencia no bloquea el stamp (los entornos "
            "creados con create_all lo conservan), pero conviene revisarlo."
        )
        print()

    partial = find_partial(statuses)
    if partial:
        print("PARCIAL — no se cambia nada.", file=sys.stderr)
        for status in partial:
            missing = ", ".join(e.describe() for e in status.missing)
            print(f"  {status.revision.revision}: faltan {missing}", file=sys.stderr)
        print(
            "\nUna revisión a medias no la produce ninguna migración. Sellarla "
            "registraría una mentira y ocultaría el objeto faltante para siempre; "
            "aplicarla con `upgrade` es justo lo que este script no hace. "
            "Requiere revisión humana.",
            file=sys.stderr,
        )
        return EXIT_PARTIAL

    target = highest_stampable(statuses)
    if target is None:
        print("Ninguna revisión de 012-016 está presente. Nada que sellar.")
        return EXIT_OK

    pending = stamp_path(statuses, recorded, target)
    if not pending:
        print(f"Convergente: alembic_version ({recorded}) ya cubre el esquema.")
        return EXIT_OK

    print(f"Revisiones presentes pero NO registradas ({len(pending)}): {', '.join(pending)}")

    if not args.stamp:
        print("\nModo lectura. Para registrarlas: " "python scripts/alembic_converge.py --stamp")
        if len(pending) > args.max_drift:
            print(
                f"\nDESVÍO: {len(pending)} revisión(es) aplicadas a mano sin registrar "
                f"(máximo tolerado: {args.max_drift}).",
                file=sys.stderr,
            )
            return EXIT_BEHIND
        return EXIT_OK

    if not args.yes and sys.stdin.isatty():
        answer = input(f"¿Sellar hasta {target} en {redact(url)}? [escribe 'si'] ")
        if answer.strip().lower() not in {"si", "sí"}:
            print("Cancelado. No se cambió nada.")
            return EXIT_OK

    for revision in pending:
        print(f"alembic stamp {revision} ...", end=" ", flush=True)
        result = stamp(revision, url)
        if result.returncode != 0:
            print("FALLÓ")
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            print(
                f"\nSe detuvo en {revision}. alembic_version queda en la última "
                "revisión sellada con éxito, que sigue siendo cierta.",
                file=sys.stderr,
            )
            return EXIT_ERROR
        print("ok")

    print(f"\nConvergente: alembic_version = {target}")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
