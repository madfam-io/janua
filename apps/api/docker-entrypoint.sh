#!/bin/bash
set -e

# Janua API Docker Entrypoint
# Runs database migrations before starting the application

echo "=== Janua API Startup ==="

# Wait for database to be ready (with timeout)
echo "Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ.get('DATABASE_URL', ''))
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('Database is ready')
" 2>/dev/null; then
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Attempt $RETRY_COUNT/$MAX_RETRIES - Database not ready, waiting..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: Database connection failed after $MAX_RETRIES attempts"
    exit 1
fi

# Run database migrations if alembic is available
if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
    echo "Running database migrations..."

    # Check if alembic_version table exists (first-time setup)
    NEEDS_STAMP=$(python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ.get('DATABASE_URL', ''))
with engine.connect() as conn:
    try:
        result = conn.execute(text('SELECT COUNT(*) FROM alembic_version'))
        count = result.scalar()
        print('no' if count > 0 else 'yes')
    except Exception:
        print('yes')
" 2>/dev/null || echo "yes")

    if [ "$NEEDS_STAMP" = "yes" ]; then
        echo "  First-time migration setup - stamping current schema..."
        # Stamp with base revision for existing databases
        alembic stamp head || {
            echo "  Warning: Could not stamp database, attempting fresh migration..."
            alembic upgrade head || {
                echo "  Warning: Migration failed, but continuing startup..."
            }
        }
    else
        # Run pending migrations
        alembic upgrade head || {
            echo "  Warning: Migration failed, but continuing startup..."
        }
    fi

    echo "  Migrations complete"
else
    echo "  Skipping migrations (alembic not configured)"
fi

echo "Starting Janua API..."
exec "$@"
