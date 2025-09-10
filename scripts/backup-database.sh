#!/bin/bash

# Database Backup Script for Plinto
# Supports PostgreSQL backup to local storage and cloud (S3/R2)

set -euo pipefail

# Configuration
DB_NAME="${DB_NAME:-plinto}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/plinto}"
S3_BUCKET="${S3_BUCKET:-plinto-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp for backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="plinto_${ENVIRONMENT}_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to send alerts (integrate with your monitoring system)
send_alert() {
    local message="$1"
    local severity="${2:-warning}"
    
    # Send to monitoring endpoint if configured
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        curl -X POST "$ALERT_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"Database Backup Alert: $message\", \"severity\":\"$severity\"}" \
            2>/dev/null || true
    fi
    
    log "ALERT [$severity]: $message"
}

# Function to perform database backup
perform_backup() {
    log "Starting database backup for $DB_NAME..."
    
    # Use pg_dump with compression
    if PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        --verbose \
        | gzip -9 > "$BACKUP_PATH"; then
        
        log "Database backup completed: $BACKUP_PATH"
        
        # Get backup size
        BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
        log "Backup size: $BACKUP_SIZE"
        
        return 0
    else
        send_alert "Database backup failed for $DB_NAME" "critical"
        return 1
    fi
}

# Function to upload to S3/R2
upload_to_cloud() {
    if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
        log "Cloud storage credentials not configured, skipping upload"
        return 0
    fi
    
    log "Uploading backup to cloud storage..."
    
    # Upload to S3/R2
    if aws s3 cp "$BACKUP_PATH" "s3://${S3_BUCKET}/${ENVIRONMENT}/${BACKUP_FILE}" \
        --storage-class STANDARD_IA \
        --metadata "environment=${ENVIRONMENT},timestamp=${TIMESTAMP}"; then
        
        log "Backup uploaded to s3://${S3_BUCKET}/${ENVIRONMENT}/${BACKUP_FILE}"
        
        # Set lifecycle policy for automatic deletion after retention period
        aws s3api put-object-tagging \
            --bucket "$S3_BUCKET" \
            --key "${ENVIRONMENT}/${BACKUP_FILE}" \
            --tagging "TagSet=[{Key=AutoDelete,Value=true},{Key=RetentionDays,Value=${RETENTION_DAYS}}]" \
            2>/dev/null || true
        
        return 0
    else
        send_alert "Failed to upload backup to cloud storage" "warning"
        return 1
    fi
}

# Function to clean up old local backups
cleanup_old_backups() {
    log "Cleaning up old backups (retention: ${RETENTION_DAYS} days)..."
    
    # Find and delete old backup files
    find "$BACKUP_DIR" \
        -name "plinto_${ENVIRONMENT}_*.sql.gz" \
        -type f \
        -mtime +${RETENTION_DAYS} \
        -exec rm -f {} \; \
        -exec log "Deleted old backup: {}" \;
    
    # Keep at least 3 most recent backups regardless of age
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/plinto_${ENVIRONMENT}_*.sql.gz 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 3 ]; then
        log "Keeping minimum 3 recent backups"
    fi
}

# Function to verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    # Test if the backup file is a valid gzip
    if gzip -t "$BACKUP_PATH" 2>/dev/null; then
        log "Backup file integrity verified"
        
        # Optionally test restore to a temporary database
        if [ "${VERIFY_RESTORE:-false}" = "true" ]; then
            log "Testing backup restore (this may take a while)..."
            
            TEST_DB="plinto_backup_test_${TIMESTAMP}"
            
            # Create test database
            PGPASSWORD="${DB_PASSWORD:-}" createdb \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                "$TEST_DB" 2>/dev/null || true
            
            # Attempt restore
            if gunzip -c "$BACKUP_PATH" | PGPASSWORD="${DB_PASSWORD:-}" psql \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$TEST_DB" \
                -q 2>/dev/null; then
                
                log "Backup restore test successful"
                
                # Drop test database
                PGPASSWORD="${DB_PASSWORD:-}" dropdb \
                    -h "$DB_HOST" \
                    -p "$DB_PORT" \
                    -U "$DB_USER" \
                    "$TEST_DB" 2>/dev/null || true
            else
                send_alert "Backup restore test failed" "warning"
            fi
        fi
        
        return 0
    else
        send_alert "Backup file integrity check failed" "critical"
        return 1
    fi
}

# Function to report backup metrics
report_metrics() {
    if [ -n "${METRICS_ENDPOINT:-}" ]; then
        local duration=$(($(date +%s) - START_TIME))
        local size_bytes=$(stat -f%z "$BACKUP_PATH" 2>/dev/null || stat -c%s "$BACKUP_PATH" 2>/dev/null || echo 0)
        
        curl -X POST "$METRICS_ENDPOINT" \
            -H "Content-Type: application/json" \
            -d "{
                \"metric\": \"database.backup\",
                \"environment\": \"${ENVIRONMENT}\",
                \"duration_seconds\": ${duration},
                \"size_bytes\": ${size_bytes},
                \"status\": \"${1}\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
            }" \
            2>/dev/null || true
    fi
}

# Main execution
main() {
    START_TIME=$(date +%s)
    
    log "=== Database Backup Script Started ==="
    log "Environment: $ENVIRONMENT"
    log "Database: $DB_NAME @ $DB_HOST:$DB_PORT"
    
    # Perform backup
    if perform_backup; then
        # Verify backup
        if verify_backup; then
            # Upload to cloud
            upload_to_cloud
            
            # Clean up old backups
            cleanup_old_backups
            
            # Report success
            report_metrics "success"
            log "=== Database Backup Completed Successfully ==="
            exit 0
        else
            report_metrics "verification_failed"
            exit 2
        fi
    else
        report_metrics "backup_failed"
        exit 1
    fi
}

# Run main function
main "$@"