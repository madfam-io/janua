#!/bin/bash
#
# Janua PostgreSQL Backup & Restore Script
# =========================================
#
# Usage:
#   ./backup-restore.sh backup              # Create immediate backup
#   ./backup-restore.sh restore <file>      # Restore from backup
#   ./backup-restore.sh list                # List available backups
#   ./backup-restore.sh verify <file>       # Verify backup integrity
#
set -euo pipefail

BACKUP_DIR="/var/backups/janua/postgres"
CONTAINER_NAME="janua-postgres-backup"
POSTGRES_CONTAINER="janua-postgres"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

backup() {
    log_info "Creating immediate backup..."

    # Trigger backup in the backup container
    docker exec "$CONTAINER_NAME" /backup.sh

    if [ $? -eq 0 ]; then
        LATEST=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
        if [ -n "$LATEST" ]; then
            log_info "Backup created: $LATEST"
            log_info "Size: $(du -h "$LATEST" | cut -f1)"
        fi
    else
        log_error "Backup failed!"
        exit 1
    fi
}

list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    echo ""

    if [ -d "$BACKUP_DIR" ]; then
        ls -lhtr "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found"
    else
        log_warn "Backup directory does not exist: $BACKUP_DIR"
    fi
}

verify_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Verifying backup: $backup_file"

    # Check if file is valid gzip
    if gzip -t "$backup_file" 2>/dev/null; then
        log_info "Compression: Valid gzip"
    else
        log_error "Compression: Invalid or corrupted gzip file"
        exit 1
    fi

    # Check pg_restore can read the file
    if gunzip -c "$backup_file" | pg_restore -l - >/dev/null 2>&1; then
        log_info "Format: Valid PostgreSQL custom format"
    else
        log_warn "Could not validate PostgreSQL format (may be plain SQL)"
    fi

    # Show file info
    log_info "File size: $(du -h "$backup_file" | cut -f1)"
    log_info "Created: $(stat -c %y "$backup_file" 2>/dev/null || stat -f %Sm "$backup_file")"

    log_info "Verification complete!"
}

restore_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "WARNING: This will restore the database from backup!"
    log_warn "Current data will be OVERWRITTEN!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled."
        exit 0
    fi

    log_info "Stopping API services..."
    docker stop janua-api 2>/dev/null || true

    log_info "Restoring from: $backup_file"

    # Drop and recreate database
    docker exec -i "$POSTGRES_CONTAINER" psql -U janua -d postgres -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = 'janua' AND pid <> pg_backend_pid();
    " 2>/dev/null || true

    docker exec -i "$POSTGRES_CONTAINER" psql -U janua -d postgres -c "DROP DATABASE IF EXISTS janua;"
    docker exec -i "$POSTGRES_CONTAINER" psql -U janua -d postgres -c "CREATE DATABASE janua;"

    # Restore
    gunzip -c "$backup_file" | docker exec -i "$POSTGRES_CONTAINER" pg_restore \
        -U janua \
        -d janua \
        --no-owner \
        --no-privileges \
        --if-exists \
        --clean \
        2>&1 | grep -v "does not exist, skipping" || true

    if [ $? -eq 0 ]; then
        log_info "Database restored successfully!"
    else
        log_error "Restore completed with warnings (some objects may not exist)"
    fi

    log_info "Starting API services..."
    docker start janua-api 2>/dev/null || true

    log_info "Restore complete!"
}

# Main
case "${1:-}" in
    backup)
        backup
        ;;
    list)
        list_backups
        ;;
    verify)
        if [ -z "${2:-}" ]; then
            log_error "Usage: $0 verify <backup_file>"
            exit 1
        fi
        verify_backup "$2"
        ;;
    restore)
        if [ -z "${2:-}" ]; then
            log_error "Usage: $0 restore <backup_file>"
            exit 1
        fi
        restore_backup "$2"
        ;;
    *)
        echo "Janua PostgreSQL Backup & Restore"
        echo ""
        echo "Usage:"
        echo "  $0 backup              Create immediate backup"
        echo "  $0 restore <file>      Restore from backup"
        echo "  $0 list                List available backups"
        echo "  $0 verify <file>       Verify backup integrity"
        echo ""
        exit 1
        ;;
esac
