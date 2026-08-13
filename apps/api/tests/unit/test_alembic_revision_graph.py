"""Structural invariants for the alembic revision graph.

These tests exist because both invariants were violated in main at once, and
each failure was silent in a different way:

1. `004_add_guest_invites.down_revision` was "003_add_product_tiers" -- the
   *filename stem* of 003, not its revision id, which is '003'. Migrations
   000-003 use bare numeric ids; 004+ use `NNN_slug` ids, and the convention
   change was not carried into the parent pointer. Every alembic command
   (history/heads/current/stamp/upgrade) raised
   `KeyError: '003_add_product_tiers'`, so nothing from 004 onwards could be
   applied. Production sat at revision '002' for months while the container
   entrypoint swallowed the error and logged "Migrations complete".

2. `006`'s revision id was "006_add_api_key_rate_limit_and_revoked" -- 38
   characters. `alembic_version.version_num` is VARCHAR(32), so alembic could
   never record that revision: the write raised StringDataRightTruncation and
   rolled the entire upgrade back. Defect 1 masked defect 2 by stopping every
   upgrade before it reached 006.

Parsing is done with `ast` rather than by importing the modules or building an
alembic ScriptDirectory, so these tests need no database, no settings and no
app imports -- they check the files themselves and cannot be defeated by an
unimportable environment.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"

# alembic creates alembic_version.version_num as VARCHAR(32). A revision id
# longer than this can never be recorded, so the migration can never apply.
MAX_REVISION_ID_LENGTH = 32


def _literal(module: ast.Module, name: str):
    """Return the literal value assigned to a module-level `name`, if any."""
    for node in module.body:
        targets = []
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


def _load_graph() -> dict[str, dict]:
    """Map revision id -> {down: parent-or-None, file: filename}."""
    graph: dict[str, dict] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue
        module = ast.parse(path.read_text(), filename=str(path))
        revision = _literal(module, "revision")
        assert revision is not None, f"{path.name} defines no `revision`"
        assert revision not in graph, (
            f"duplicate revision id {revision!r}: "
            f"{graph[revision]['file']} and {path.name}"
        )
        graph[revision] = {"down": _literal(module, "down_revision"), "file": path.name}
    return graph


GRAPH = _load_graph()


def test_versions_directory_is_not_empty() -> None:
    assert GRAPH, f"no migrations found in {VERSIONS_DIR}"


@pytest.mark.parametrize("revision", sorted(GRAPH))
def test_revision_id_fits_alembic_version_column(revision: str) -> None:
    """A revision id longer than VARCHAR(32) can never be recorded."""
    assert len(revision) <= MAX_REVISION_ID_LENGTH, (
        f"revision id {revision!r} in {GRAPH[revision]['file']} is "
        f"{len(revision)} chars; alembic_version.version_num is "
        f"VARCHAR({MAX_REVISION_ID_LENGTH}). Applying it fails with "
        f"StringDataRightTruncation and rolls the whole upgrade back. "
        f"Shorten the revision id."
    )


@pytest.mark.parametrize("revision", sorted(GRAPH))
def test_down_revision_resolves(revision: str) -> None:
    """Every parent pointer must name a revision that actually exists."""
    down = GRAPH[revision]["down"]
    if down is None:
        return
    parents = down if isinstance(down, (list, tuple)) else [down]
    for parent in parents:
        assert parent in GRAPH, (
            f"{GRAPH[revision]['file']} has down_revision={parent!r}, which is "
            f"not a known revision id. Known ids: {sorted(GRAPH)}. "
            f"(A filename stem is not a revision id.)"
        )


def test_exactly_one_base() -> None:
    bases = [rev for rev, meta in GRAPH.items() if meta["down"] is None]
    assert len(bases) == 1, f"expected exactly 1 base revision, found {bases}"


def test_exactly_one_head() -> None:
    """More than one head means `alembic upgrade head` is ambiguous."""
    referenced: set[str] = set()
    for meta in GRAPH.values():
        down = meta["down"]
        if down is None:
            continue
        referenced.update(down if isinstance(down, (list, tuple)) else [down])
    heads = sorted(set(GRAPH) - referenced)
    assert len(heads) == 1, (
        f"expected exactly 1 head, found {heads}. Add a merge revision "
        f"(`alembic merge`) rather than repointing an existing migration."
    )


def test_graph_is_acyclic_and_fully_connected() -> None:
    """Walking from the single head must reach every revision exactly once."""
    referenced: set[str] = set()
    for meta in GRAPH.values():
        down = meta["down"]
        if down is None:
            continue
        referenced.update(down if isinstance(down, (list, tuple)) else [down])
    heads = sorted(set(GRAPH) - referenced)
    assert len(heads) == 1, f"need exactly one head to walk, found {heads}"

    seen: list[str] = []
    cursor = heads[0]
    while cursor is not None:
        assert cursor not in seen, f"cycle detected in revision chain at {cursor!r}"
        seen.append(cursor)
        down = GRAPH[cursor]["down"]
        if isinstance(down, (list, tuple)):
            pytest.skip("merge revision present; linear walk does not apply")
        cursor = down

    unreachable = sorted(set(GRAPH) - set(seen))
    assert not unreachable, (
        f"revisions unreachable from head: {unreachable}. They would never be "
        f"applied by `alembic upgrade head`."
    )
