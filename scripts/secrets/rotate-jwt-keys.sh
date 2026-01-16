#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# MADFAM JWT Key Rotation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Rotates RS256 JWT signing keys for the MADFAM ecosystem.
# Implements 24-hour grace period by keeping old keys temporarily.
#
# Usage:
#   ./rotate-jwt-keys.sh --project janua [--dry-run]
#   ./rotate-jwt-keys.sh --project janua --cleanup (remove old keys after grace period)
#
# Key rotation process:
#   1. Generate new RS256 keypair
#   2. Store old keys with -old suffix
#   3. Update secrets with both old and new keys
#   4. Rolling restart services
#   5. After 24h, run with --cleanup to remove old keys
#
# Exit codes:
#   0 - Success
#   1 - Validation/permission error
#   2 - Key generation error
#   3 - Kubernetes update error
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
PROJECT=""
DRY_RUN=false
CLEANUP_MODE=false
NAMESPACE=""
SECRET_NAME=""
KEY_SIZE=2048
GRACE_PERIOD_HOURS=24

# Temp directory for keys
TEMP_DIR=""

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Usage information
usage() {
    cat << EOF
MADFAM JWT Key Rotation Script

Usage: $0 --project <janua|enclii> [OPTIONS]

Required:
  --project <name>    Project name (janua or enclii)

Options:
  --dry-run           Show what would be done without making changes
  --cleanup           Remove old keys (run 24h after rotation)
  --namespace <ns>    Kubernetes namespace (default: project name)
  --secret <name>     Secret name (default: <project>-secrets)
  --key-size <bits>   RSA key size (default: 2048)
  --help              Show this help message

Key Names in Secret:
  jwt-private-key     Current private key
  jwt-public-key      Current public key
  jwt-private-key-old Previous private key (during grace period)
  jwt-public-key-old  Previous public key (during grace period)

Examples:
  # Initial rotation
  $0 --project janua --dry-run
  $0 --project janua

  # After 24 hours, cleanup old keys
  $0 --project janua --cleanup

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
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --cleanup)
                CLEANUP_MODE=true
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
            --key-size)
                KEY_SIZE="$2"
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

# Create temp directory
setup_temp_dir() {
    TEMP_DIR=$(mktemp -d)
    trap cleanup_temp EXIT
}

# Cleanup temp directory
cleanup_temp() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

# Generate new RS256 keypair
generate_keypair() {
    log_step "Generating new RS256 keypair (${KEY_SIZE} bits)..."

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would generate new keypair"
        return 0
    fi

    # Generate private key
    if ! openssl genrsa -out "$TEMP_DIR/new_private.pem" "$KEY_SIZE" 2>/dev/null; then
        log_error "Failed to generate private key"
        exit 2
    fi

    # Extract public key
    if ! openssl rsa -in "$TEMP_DIR/new_private.pem" -pubout -out "$TEMP_DIR/new_public.pem" 2>/dev/null; then
        log_error "Failed to extract public key"
        exit 2
    fi

    log_success "New keypair generated"

    # Display key fingerprints for verification
    log_info "New key fingerprint:"
    openssl rsa -in "$TEMP_DIR/new_private.pem" -pubout -outform DER 2>/dev/null | \
        openssl sha256 | cut -d' ' -f2 | head -c 16
    echo ""
}

# Get current keys from K8s secret
backup_current_keys() {
    log_step "Backing up current keys..."

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would backup current keys"
        return 0
    fi

    # Get current private key
    kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.data.jwt-private-key}' | base64 -d > "$TEMP_DIR/old_private.pem" 2>/dev/null || true

    # Get current public key
    kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.data.jwt-public-key}' | base64 -d > "$TEMP_DIR/old_public.pem" 2>/dev/null || true

    if [[ -s "$TEMP_DIR/old_private.pem" ]]; then
        log_success "Current keys backed up"
    else
        log_warn "No existing JWT keys found (first-time setup?)"
    fi
}

# Update Kubernetes secret with new keys
update_k8s_secret() {
    log_step "Updating Kubernetes secret..."

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would update secret with new keys and backup old keys"
        return 0
    fi

    # Encode new keys
    local new_private_b64 new_public_b64
    new_private_b64=$(base64 -w0 "$TEMP_DIR/new_private.pem" 2>/dev/null || base64 "$TEMP_DIR/new_private.pem")
    new_public_b64=$(base64 -w0 "$TEMP_DIR/new_public.pem" 2>/dev/null || base64 "$TEMP_DIR/new_public.pem")

    # Build patch JSON
    local patch_ops="["
    patch_ops+="{\"op\": \"replace\", \"path\": \"/data/jwt-private-key\", \"value\":\"$new_private_b64\"},"
    patch_ops+="{\"op\": \"replace\", \"path\": \"/data/jwt-public-key\", \"value\":\"$new_public_b64\"}"

    # Add old keys if they exist
    if [[ -s "$TEMP_DIR/old_private.pem" ]]; then
        local old_private_b64 old_public_b64
        old_private_b64=$(base64 -w0 "$TEMP_DIR/old_private.pem" 2>/dev/null || base64 "$TEMP_DIR/old_private.pem")
        old_public_b64=$(base64 -w0 "$TEMP_DIR/old_public.pem" 2>/dev/null || base64 "$TEMP_DIR/old_public.pem")

        patch_ops+=",{\"op\": \"add\", \"path\": \"/data/jwt-private-key-old\", \"value\":\"$old_private_b64\"}"
        patch_ops+=",{\"op\": \"add\", \"path\": \"/data/jwt-public-key-old\", \"value\":\"$old_public_b64\"}"
    fi
    patch_ops+="]"

    # Apply patch
    if ! kubectl patch secret "$SECRET_NAME" -n "$NAMESPACE" --type='json' -p="$patch_ops"; then
        log_error "Failed to update Kubernetes secret"
        exit 3
    fi

    log_success "Kubernetes secret updated with new keys"

    if [[ -s "$TEMP_DIR/old_private.pem" ]]; then
        log_info "Old keys preserved with -old suffix for ${GRACE_PERIOD_HOURS}h grace period"
    fi
}

# Remove old keys (cleanup mode)
cleanup_old_keys() {
    log_step "Removing old JWT keys from secret..."

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] Would remove jwt-private-key-old and jwt-public-key-old"
        return 0
    fi

    # Check if old keys exist
    local has_old_keys
    has_old_keys=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.data.jwt-private-key-old}' 2>/dev/null || echo "")

    if [[ -z "$has_old_keys" ]]; then
        log_warn "No old keys found to remove"
        return 0
    fi

    # Remove old keys
    local patch_ops="["
    patch_ops+="{\"op\": \"remove\", \"path\": \"/data/jwt-private-key-old\"},"
    patch_ops+="{\"op\": \"remove\", \"path\": \"/data/jwt-public-key-old\"}"
    patch_ops+="]"

    if ! kubectl patch secret "$SECRET_NAME" -n "$NAMESPACE" --type='json' -p="$patch_ops"; then
        log_error "Failed to remove old keys"
        exit 3
    fi

    log_success "Old keys removed from secret"
}

# Trigger rolling restart
rolling_restart() {
    log_step "Triggering rolling restart..."

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
        return 0
    fi

    # Wait for rollout
    for deployment in $deployments; do
        log_info "Waiting for $deployment rollout..."
        kubectl rollout status "$deployment" -n "$NAMESPACE" --timeout=180s || {
            log_warn "Rollout status check timed out for $deployment"
        }
    done

    log_success "Rolling restart completed"
}

# Show cross-project notification
show_cross_project_notice() {
    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_warn "CROSS-PROJECT NOTIFICATION REQUIRED"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""

    if [[ "$PROJECT" == "janua" ]]; then
        echo "  The Enclii project uses Janua for OIDC authentication."
        echo "  After this rotation, existing Enclii sessions will continue"
        echo "  working during the ${GRACE_PERIOD_HOURS}h grace period."
        echo ""
        echo "  Notify the Enclii team:"
        echo "    - JWT keys have been rotated"
        echo "    - New public key is now active"
        echo "    - Old tokens will be valid for ${GRACE_PERIOD_HOURS}h"
        echo ""
    fi
}

# Show registry update reminder
show_registry_reminder() {
    local today
    today=$(date +%Y-%m-%d)
    local next_rotation
    next_rotation=$(date -d "+365 days" +%Y-%m-%d 2>/dev/null || date -v+365d +%Y-%m-%d 2>/dev/null || echo "CALCULATE_DATE")

    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_success "JWT keys rotated successfully!"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""
    log_warn "IMPORTANT: Update SECRETS_REGISTRY.yaml with:"
    echo ""
    echo "  - id: ${PROJECT}-jwt-private-key"
    echo "    last_rotated: \"$today\""
    echo "    next_rotation: \"$next_rotation\""
    echo ""
    echo "  - id: ${PROJECT}-jwt-public-key"
    echo "    last_rotated: \"$today\""
    echo "    next_rotation: \"$next_rotation\""
    echo ""

    show_cross_project_notice

    log_warn "After ${GRACE_PERIOD_HOURS}h, run cleanup:"
    echo ""
    echo "  $0 --project $PROJECT --cleanup"
    echo ""
}

# Main execution
main() {
    parse_args "$@"

    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_info "MADFAM JWT Key Rotation"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""
    log_info "Project:   $PROJECT"
    log_info "Namespace: $NAMESPACE"
    log_info "Secret:    $SECRET_NAME"
    log_info "Key Size:  $KEY_SIZE bits"
    log_info "Mode:      $(if $CLEANUP_MODE; then echo "Cleanup (remove old keys)"; else echo "Rotation"; fi)"
    log_info "Dry Run:   $DRY_RUN"
    echo ""

    # Verify prerequisites
    verify_prerequisites

    if [[ "$CLEANUP_MODE" == true ]]; then
        # Cleanup mode - just remove old keys
        cleanup_old_keys
        rolling_restart
        log_success "Old keys cleaned up. Rotation complete."
        exit 0
    fi

    # Normal rotation mode
    setup_temp_dir

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "═══════════════════════════════════════════════════════════════"
        log_warn "DRY-RUN MODE - No changes will be made"
        log_warn "═══════════════════════════════════════════════════════════════"
    fi

    # Execute rotation steps
    backup_current_keys
    generate_keypair
    update_k8s_secret
    rolling_restart

    # Show reminders
    show_registry_reminder
}

main "$@"
