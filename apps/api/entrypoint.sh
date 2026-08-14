#!/bin/bash
# No set -e — the API must start even if DB/migrations fail.
# FastAPI handles DB unavailability at request time.

echo "=== Janua API Startup ==="

# Run database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations..."

    # Wait for database to be ready (max 30 seconds)
    DB_READY=false
    for i in {1..30}; do
        if python -c "
import asyncio
import asyncpg

async def check():
    try:
        conn = await asyncpg.connect('$DATABASE_URL', timeout=5)
        await conn.close()
        return True
    except:
        return False

exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
            echo "Database is ready"
            DB_READY=true
            break
        fi
        echo "Waiting for database... ($i/30)"
        sleep 1
    done

    # Run Alembic migrations only if DB is reachable
    if [ "$DB_READY" = true ]; then
        cd /app
        # The revision tree must resolve to exactly one head. This reads
        # alembic/versions/ only (no database), so it is environment-
        # independent: a failure here is always a code defect.
        if ! HEADS_OUT=$(alembic heads 2>&1) || [ "$(printf '%s\n' "$HEADS_OUT" | grep -c '(head)')" -ne 1 ]; then
            echo "❌ FATAL: alembic revision tree is broken (not exactly 1 resolvable head)."
            echo "$HEADS_OUT"
            exit 1
        fi

        # Applying migrations is opt-in -- see docker-entrypoint.sh for the
        # rationale (deliberate operator action, and replicas race DDL).
        if [ "${JANUA_APPLY_MIGRATIONS:-false}" = "true" ]; then
            if alembic upgrade head 2>&1; then
                echo "✅ Database migrations completed successfully"
            else
                echo "❌ FATAL: migration failed. Refusing to start on an unmigrated schema."
                exit 1
            fi
        else
            echo "⚠️ MIGRATION_DRIFT: not applying migrations (JANUA_APPLY_MIGRATIONS is not 'true')."
        fi
    else
        echo "⚠️ Database not reachable after 30s — starting API anyway"
    fi
else
    echo "⚠️ DATABASE_URL not set, skipping migrations"
fi

echo "Starting Janua API..."
exec "$@"
