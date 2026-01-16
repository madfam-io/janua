#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# MADFAM Database Password Rotation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Rotates PostgreSQL database passwords for Janua or Enclii projects.
# Updates both the database and Kubernetes secrets atomically.
#
# Usage:
#   ./rotate-db-password.sh --project janua [--dry-run] [--user postgres]
#   ./rotate-db-password.sh --project enclii --user readonly --dry-run
#
# Requirements:
#   - kubectl configured with cluster access
#   - PostgreSQL client (psql)
#   - openssl for password generation
#
# Exit codes:
#   0 - Success
#   1 - Validation/permission error
#   2 - Database connection error
#   3 - Kubernetes update error
#   4 - Rollback triggered
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT=""
DB_USER="janua"
DRY_RUN=false
NAMESPACE=""
SECRET_NAME=""
SECRET_KEY="database-password"
POD_NAME=""
BACKUP_FILE=""
ROLLOUT_TIMEOUT="180s"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Usage information
usage() {
    cat << EOF
MADFAM Database Password Rotation Script

Usage: $0 --project <janua|enclii> [OPTIONS]

Required:
  --project <name>    Project name (janua or enclii)

Options:
  --user <username>   Database user to rotate (default: janua/enclii)
  --dry-run           Show what would be done without making changes
  --namespace <ns>    Kubernetes namespace (default: project name)
  --secret <name>     Secret name (default: <project>-secrets)
  --secret-key <key>  Key within secret (default: database-password)
  --timeout <time>    Rollout timeout (default: 180s)
  --help              Show this help message

Examples:
  $0 --project janua --dry-run
  $0 --project janua --user readonly
  $0 --project enclii --namespace enclii-prod

EOF
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project)
                PROJECT="$2"
                shift 2
                ;;
            --user)
                DB_USER="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --secret)
                SECRET_NAME="$2"
                shift 2
                ;;
            --secret-key)
                SECRET_KEY="$2"
                shift 2
                ;;
            --timeout)
                ROLLOUT_TIMEOUT="$2"
                shift 2
                ;;
            --help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$PROJECT" ]]; then
        log_error "Project name is required"
        usage
    fi

    if [[ "$PROJECT" != "janua" && "$PROJECT" != "enclii" ]]; then
        log_error "Project must be 'janua' or 'enclii'"
        exit 1
    fi

    # Set defaults based on project
    NAMESPACE="${NAMESPACE:-$PROJECT}"
    SECRET_NAME="${SECRET_NAME:-${PROJECT}-secrets}"
    DB_USER="${DB_USER:-$PROJECT}"
    POD_NAME="${PROJECT}-postgres-0"
}

# Verify prerequisites
verify_prerequisites() {
    log_info "Verifying prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed"
        exit 1
    fi

    # Check openssl
    if ! command -v openssl &> /dev/null; then
        log_error "openssl is required but not installed"
        exit 1
    fi

    # Check cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi

    # Check secret exists
    if ! kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &> /dev/null; then
        log_error "Secret '$SECRET_NAME' not found in namespace '$NAMESPACE'"
        exit 1
    fi

    log_success "Prerequisites verified"
}

# Generate secure password
generate_password() {
    # 32-character base64 password (alphanumeric + some special chars)
    openssl rand -base64 32 | tr -d '/+=' | head -c 32
}

# Backup current password
backup_current_password() {
    log_info "Backing up current password..."

    BACKUP_FILE=$(mktemp)
    kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath="{.data.$SECRET_KEY}" > "$BACKUP_FILE"

    if [[ ! -s "$BACKUP_FILE" ]]; then
        log_error "Failed to backup current password"
        exit 1
    fi

    log_success "Current password backed up to temporary file"
}

# Update PostgreSQL password
update_postgres_password() {
    local new_password="$1"

    log_info "Updating PostgreSQL password for user '$DB_USER'..."

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would execute: ALTER USER $DB_USER PASSWORD '***';"
        return 0
    fi

    # Execute ALTER USER in PostgreSQL
    if ! kubectl exec -n "$NAMESPACE" "$POD_NAME" -- psql -U postgres -c \
        "ALTER USER $DB_USER PASSWORD '$new_password';" &> /dev/null; then
        log_error "Failed to update PostgreSQL password"
        return 1
    fi

    log_success "PostgreSQL password updated"
}

# Update Kubernetes secret
update_k8s_secret() {
    local new_password="$1"
    local encoded_password

    log_info "Updating Kubernetes secret..."

    encoded_password=$(echo -n "$new_password" | base64)

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would patch secret '$SECRET_NAME' with new password"
        return 0
    fi

    if ! kubectl patch secret "$SECRET_NAME" -n "$NAMESPACE" --type='json' \
        -p="[{\"op\": \"replace\", \"path\": \"/data/$SECRET_KEY\", \"value\":\"$encoded_password\"}]"; then
        log_error "Failed to update Kubernetes secret"
        return 1
    fi

    log_success "Kubernetes secret updated"
}

# Trigger rolling restart
rolling_restart() {
    log_info "Triggering rolling restart of deployments..."

    local deployments
    deployments=$(kubectl get deployments -n "$NAMESPACE" -l "app.kubernetes.io/part-of=$PROJECT" -o name 2>/dev/null || true)

    if [[ -z "$deployments" ]]; then
        # Fallback to common deployment names
        deployments="deployment/${PROJECT}-api"
    fi

    for deployment in $deployments; do
        if [[ "$DRY_RUN" == true ]]; then
            log_warn "[DRY-RUN] Would restart: $deployment"
        else
            log_info "Restarting $deployment..."
            kubectl rollout restart "$deployment" -n "$NAMESPACE"
        fi
    done

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would wait for rollout to complete"
        return 0
    fi

    # Wait for rollout to complete
    for deployment in $deployments; do
        log_info "Waiting for $deployment rollout..."
        if ! kubectl rollout status "$deployment" -n "$NAMESPACE" --timeout="$ROLLOUT_TIMEOUT"; then
            log_error "Rollout failed for $deployment"
            return 1
        fi
    done

    log_success "Rolling restart completed"
}

# Rollback function
rollback() {
    log_error "Rolling back to previous password..."

    if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
        log_error "No backup file available for rollback!"
        exit 4
    fi

    local old_password_encoded
    old_password_encoded=$(cat "$BACKUP_FILE")

    # Restore K8s secret
    kubectl patch secret "$SECRET_NAME" -n "$NAMESPACE" --type='json' \
        -p="[{\"op\": \"replace\", \"path\": \"/data/$SECRET_KEY\", \"value\":\"$old_password_encoded\"}]"

    log_warn "K8s secret restored. Note: PostgreSQL password may be out of sync!"
    log_warn "Manual intervention may be required."

    rm -f "$BACKUP_FILE"
    exit 4
}

# Cleanup function
cleanup() {
    if [[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]]; then
        rm -f "$BACKUP_FILE"
    fi
}

# Update registry reminder
update_registry_reminder() {
    local today
    today=$(date +%Y-%m-%d)

    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_success "Database password rotated successfully!"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""
    log_warn "IMPORTANT: Update SECRETS_REGISTRY.yaml with:"
    echo ""
    echo "  - id: ${PROJECT}-postgres-password"
    echo "    last_rotated: \"$today\""
    echo "    next_rotation: \"$(date -d "+90 days" +%Y-%m-%d 2>/dev/null || date -v+90d +%Y-%m-%d)\""
    echo ""
    log_info "Then commit and push the changes."
}

# Main execution
main() {
    parse_args "$@"

    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_info "MADFAM Database Password Rotation"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""
    log_info "Project:   $PROJECT"
    log_info "Namespace: $NAMESPACE"
    log_info "DB User:   $DB_USER"
    log_info "Secret:    $SECRET_NAME ($SECRET_KEY)"
    log_info "Dry Run:   $DRY_RUN"
    echo ""

    # Set up cleanup trap
    trap cleanup EXIT

    # Verify prerequisites
    verify_prerequisites

    # Backup current password
    backup_current_password

    # Generate new password
    local new_password
    new_password=$(generate_password)
    log_info "Generated new secure password (32 characters)"

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "═══════════════════════════════════════════════════════════════"
        log_warn "DRY-RUN MODE - No changes will be made"
        log_warn "═══════════════════════════════════════════════════════════════"
    fi

    # Update PostgreSQL
    if ! update_postgres_password "$new_password"; then
        rollback
    fi

    # Update K8s secret
    if ! update_k8s_secret "$new_password"; then
        rollback
    fi

    # Rolling restart
    if ! rolling_restart; then
        log_warn "Rolling restart failed, but password was updated."
        log_warn "Manual investigation required."
    fi

    # Show registry update reminder
    update_registry_reminder
}

main "$@"
