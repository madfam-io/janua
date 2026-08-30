"""Per-tenant email uniqueness — email is unique WITHIN a tenant, not globally.

The keystone schema change for the BaaS "DB-only" offering (Phase 1). Today
`users.email` is GLOBALLY unique (`ix_users_email`, a plain UNIQUE btree from
000_init). That is correct for one shared MADFAM identity pool, but it makes an
end-user pool impossible: two of a client's tenants can't both have a user
`alice@example.com`, and every client's end-users share one namespace with
MADFAM staff. Supabase/Firebase Auth give each project its own user pool; this
is what lets Janua do the same.

WHY TWO PARTIAL INDEXES, not a composite `(tenant_id, email)` + `NOT NULL`:

  The naive "drop global, add UNIQUE(tenant_id, email), make tenant_id NOT NULL"
  is wrong here on two counts:

  1. tenant_id NOT NULL is a landmine. Existing rows — MADFAM staff and every
     pre-tenant-binding signup — have tenant_id = NULL, and staff LEGITIMATELY
     belong to no single tenant (users is one table, staff + end-users, with no
     discriminator yet). Forcing NOT NULL would demand backfilling staff into
     some org they don't belong to. So tenant_id stays nullable.

  2. A single UNIQUE(tenant_id, email) SILENTLY REGRESSES the staff pool. In
     Postgres, NULLs are distinct in a unique index, so two rows with
     tenant_id = NULL and the same email would BOTH be allowed — losing today's
     guarantee that `alice@madfam.io` exists at most once among untenanted
     users.

  The correct model is therefore TWO partial unique indexes, one per pool:

    A) uq_users_tenant_email : UNIQUE (tenant_id, email) WHERE tenant_id IS NOT NULL
       → each tenant gets its own email namespace; two tenants may both hold
         alice@example.com.
    B) uq_users_email_global : UNIQUE (email)            WHERE tenant_id IS NULL
       → preserves EXACTLY today's guarantee for the untenanted / staff pool.

  Together they are equivalent to the old global index for existing (NULL-tenant)
  rows and additionally give per-tenant isolation for tenanted rows. No backfill,
  no NOT NULL, and fully reversible.

CASE SENSITIVITY: both indexes match the existing behaviour — case-SENSITIVE on
the raw email, exactly like the `ix_users_email` they replace. Case-folding is a
separate, larger decision (it would need normalization of the ~existing rows and
of every write path) and is deliberately NOT bundled in here.

SAFETY: a UNIQUE index build fails loudly if data violates it. This was verified
read-only against production before writing the migration — 0 violating groups
for BOTH indexes (30 users: 10 untenanted, 20 tenanted, no dupes in either
pool). So this applies cleanly. With that row count the brief lock from a
non-CONCURRENT build is negligible; Alembic runs migrations in a transaction, so
CONCURRENTLY (which cannot run in one) is intentionally not used.

Pairs with the app layer: the signup email-existence check is made tenant-scoped
in the same change, so the application agrees with the DB (it must — otherwise a
cross-tenant signup the DB now permits would still be rejected by a global app
check, or an app-permitted insert would hit the old DB index).
"""

from sqlalchemy import inspect, text

from alembic import op

# revision identifiers, used by Alembic.
# Keep revision ids <= 32 characters: `alembic_version.version_num` is
# VARCHAR(32) and a longer id fails the stamp write, rolling back the upgrade
# it just performed. Enforced by tests/unit/test_alembic_revision_graph.py.
# "013_per_tenant_email_uniqueness" == 31 chars.
revision = "013_per_tenant_email_uniqueness"
down_revision = "012_user_spanish_formality"
branch_labels = None
depends_on = None


TENANT_EMAIL_INDEX = "uq_users_tenant_email"
GLOBAL_EMAIL_INDEX = "uq_users_email_global"
OLD_GLOBAL_INDEX = "ix_users_email"


def _index_names(bind) -> set:
    return {ix["name"] for ix in inspect(bind).get_indexes("users")}


def upgrade() -> None:
    bind = op.get_bind()
    existing = _index_names(bind)

    # A) per-tenant uniqueness for the tenanted pool.
    if TENANT_EMAIL_INDEX not in existing:
        op.create_index(
            TENANT_EMAIL_INDEX,
            "users",
            ["tenant_id", "email"],
            unique=True,
            postgresql_where=text("tenant_id IS NOT NULL"),
        )

    # B) preserve global uniqueness for the untenanted / staff pool.
    if GLOBAL_EMAIL_INDEX not in existing:
        op.create_index(
            GLOBAL_EMAIL_INDEX,
            "users",
            ["email"],
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
        )

    # Retire the old global-unique index only AFTER both replacements exist, so
    # email uniqueness is never unenforced for even an instant during upgrade.
    existing = _index_names(bind)
    if OLD_GLOBAL_INDEX in existing:
        op.drop_index(OLD_GLOBAL_INDEX, table_name="users")


def downgrade() -> None:
    bind = op.get_bind()
    existing = _index_names(bind)

    # Restore the single global-unique index first, so uniqueness stays enforced
    # throughout the downgrade too. NOTE: downgrade is only safe if no two
    # tenants have come to share an email in the meantime (which the partial
    # indexes will have allowed). If they have, this recreation fails loudly —
    # the honest outcome, since collapsing back to a global namespace with real
    # cross-tenant duplicates would otherwise mean silent data loss.
    if OLD_GLOBAL_INDEX not in existing:
        op.create_index(OLD_GLOBAL_INDEX, "users", ["email"], unique=True)

    existing = _index_names(bind)
    if GLOBAL_EMAIL_INDEX in existing:
        op.drop_index(GLOBAL_EMAIL_INDEX, table_name="users")
    if TENANT_EMAIL_INDEX in existing:
        op.drop_index(TENANT_EMAIL_INDEX, table_name="users")
