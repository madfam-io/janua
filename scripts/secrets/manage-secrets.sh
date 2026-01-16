#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# MADFAM Secrets Management CLI
# ═══════════════════════════════════════════════════════════════════════════════
#
# Central command-line interface for secrets management operations.
#
# Usage:
#   ./manage-secrets.sh <command> [options]
#
# Commands:
#   status      Check rotation status of all secrets
#   list        List all tracked secrets
#   rotate      Rotate a specific secret
#   audit       Run full security audit
#   emergency   Emergency rotation procedures
#   update      Update registry after rotation
#   help        Show this help message
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY_PATH="$PROJECT_ROOT/infra/secrets/SECRETS_REGISTRY.yaml"
RUNBOOKS_PATH="$PROJECT_ROOT/docs/runbooks/secrets"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_header() { echo -e "\n${CYAN}═══ $1 ═══${NC}\n"; }

# ═══════════════════════════════════════════════════════════════════════════════
# Help
# ═══════════════════════════════════════════════════════════════════════════════

show_help() {
    cat << 'EOF'
MADFAM Secrets Management CLI

Usage: manage-secrets.sh <command> [options]

Commands:
  status [--json]           Check rotation status (overdue, due soon, upcoming)
  list [--project NAME]     List all tracked secrets
  rotate <secret-id>        Rotate a specific secret
  audit                     Run full security audit
  emergency [--critical]    Emergency rotation procedures
  update <secret-id>        Update registry after manual rotation
  verify                    Verify all secrets are accessible
  help                      Show this help message

Examples:
  # Check what needs rotation
  ./manage-secrets.sh status

  # Rotate database password for Janua
  ./manage-secrets.sh rotate janua-postgres-password

  # Update registry after manual OAuth rotation
  ./manage-secrets.sh update janua-oauth-google-secret

  # Emergency rotation of all critical secrets
  ./manage-secrets.sh emergency --critical

Environment Variables:
  SECRETS_REGISTRY_PATH     Override default registry location
  DRY_RUN=1                 Preview actions without making changes

EOF
}

# ═══════════════════════════════════════════════════════════════════════════════
# Status Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_status() {
    local format="text"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --json) format="json"; shift ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
    done

    log_header "Secrets Rotation Status"

    if [[ ! -f "$REGISTRY_PATH" ]]; then
        log_error "Registry not found: $REGISTRY_PATH"
        exit 1
    fi

    if command -v python3 &> /dev/null; then
        python3 "$SCRIPT_DIR/check-rotation-schedule.py" --output "$format" --registry "$REGISTRY_PATH"
    else
        log_error "Python 3 required for status check"
        log_info "Install: brew install python3 (macOS) or apt install python3 (Linux)"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# List Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_list() {
    local project_filter=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --project) project_filter="$2"; shift 2 ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
    done

    log_header "Tracked Secrets"

    if [[ ! -f "$REGISTRY_PATH" ]]; then
        log_error "Registry not found: $REGISTRY_PATH"
        exit 1
    fi

    # Simple YAML parsing with grep/awk
    echo "Project     | Secret ID                        | Policy      | Owner"
    echo "------------|----------------------------------|-------------|-------------"

    if command -v python3 &> /dev/null; then
        python3 << EOF
import yaml
with open("$REGISTRY_PATH") as f:
    registry = yaml.safe_load(f)

for project, secrets in registry.get("secrets", {}).items():
    if "$project_filter" and project != "$project_filter":
        continue
    for secret in secrets:
        sid = secret.get("id", "unknown")[:32]
        policy = secret.get("policy", "unknown")[:11]
        owner = secret.get("owner", "unknown")[:12]
        print(f"{project:11} | {sid:32} | {policy:11} | {owner}")
EOF
    else
        log_warn "Python not available, showing raw registry"
        cat "$REGISTRY_PATH"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Rotate Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_rotate() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: manage-secrets.sh rotate <secret-id>"
        exit 1
    fi

    local secret_id="$1"
    local dry_run="${DRY_RUN:-0}"

    log_header "Rotate Secret: $secret_id"

    # Determine rotation script based on secret ID
    case "$secret_id" in
        *-postgres-password|*-db-password)
            local project
            project=$(echo "$secret_id" | cut -d'-' -f1)
            log_info "Detected database password rotation for project: $project"

            if [[ "$dry_run" == "1" ]]; then
                "$SCRIPT_DIR/rotate-db-password.sh" --project "$project" --dry-run
            else
                "$SCRIPT_DIR/rotate-db-password.sh" --project "$project"
            fi
            ;;

        *-jwt-private-key|*-jwt-public-key)
            local project
            project=$(echo "$secret_id" | cut -d'-' -f1)
            log_info "Detected JWT key rotation for project: $project"

            if [[ "$dry_run" == "1" ]]; then
                "$SCRIPT_DIR/rotate-jwt-keys.sh" --project "$project" --dry-run
            else
                "$SCRIPT_DIR/rotate-jwt-keys.sh" --project "$project"
            fi
            ;;

        *-ghcr-credentials)
            log_info "GHCR credential rotation requires manual steps"
            log_info "See runbook: $RUNBOOKS_PATH/ghcr-pat-rotation.md"
            ;;

        *-oauth-google*)
            log_info "Google OAuth rotation requires manual steps"
            log_info "See runbook: $RUNBOOKS_PATH/oauth-google-rotation.md"
            ;;

        *-oauth-github*)
            log_info "GitHub OAuth rotation requires manual steps"
            log_info "See runbook: $RUNBOOKS_PATH/oauth-github-rotation.md"
            ;;

        *-stripe*)
            log_info "Stripe key rotation requires manual steps"
            log_info "See runbook: $RUNBOOKS_PATH/stripe-rotation.md"
            ;;

        *)
            log_warn "No automated rotation script for: $secret_id"
            log_info "Check runbooks at: $RUNBOOKS_PATH/"
            log_info "After manual rotation, run: ./manage-secrets.sh update $secret_id"
            ;;
    esac
}

# ═══════════════════════════════════════════════════════════════════════════════
# Update Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_update() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: manage-secrets.sh update <secret-id>"
        exit 1
    fi

    local secret_id="$1"
    local today
    today=$(date +%Y-%m-%d)

    log_header "Update Registry: $secret_id"

    if [[ ! -f "$REGISTRY_PATH" ]]; then
        log_error "Registry not found: $REGISTRY_PATH"
        exit 1
    fi

    log_info "Updating last_rotated to: $today"

    # Calculate next rotation based on policy
    if command -v python3 &> /dev/null; then
        python3 << EOF
import yaml
from datetime import datetime, timedelta

with open("$REGISTRY_PATH") as f:
    registry = yaml.safe_load(f)

# Find secret and its policy
found = False
for project, secrets in registry.get("secrets", {}).items():
    for secret in secrets:
        if secret.get("id") == "$secret_id":
            policy = secret.get("policy", "annual")
            policy_days = registry.get("rotation_policies", {}).get(policy, {}).get("days", 365)

            if policy_days:
                next_date = datetime.now() + timedelta(days=policy_days)
                print(f"Policy: {policy} ({policy_days} days)")
                print(f"Next rotation: {next_date.strftime('%Y-%m-%d')}")
            found = True
            break
    if found:
        break

if not found:
    print(f"Secret '{secret_id}' not found in registry")
EOF
    fi

    echo ""
    log_warn "Manual update required in SECRETS_REGISTRY.yaml:"
    echo ""
    echo "  - id: $secret_id"
    echo "    last_rotated: \"$today\""
    echo "    next_rotation: \"YYYY-MM-DD\"  # Calculate from policy"
    echo ""
    log_info "Then commit and push the changes:"
    echo "  git add infra/secrets/SECRETS_REGISTRY.yaml"
    echo "  git commit -m \"chore: update rotation date for $secret_id\""
    echo "  git push"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Audit Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_audit() {
    log_header "Security Audit"

    local issues=0

    # Check registry exists
    log_info "Checking registry..."
    if [[ -f "$REGISTRY_PATH" ]]; then
        log_success "Registry found"
    else
        log_error "Registry not found: $REGISTRY_PATH"
        ((issues++))
    fi

    # Check rotation status
    log_info "Checking rotation status..."
    if command -v python3 &> /dev/null; then
        local overdue
        overdue=$(python3 -c "
import yaml
from datetime import date

with open('$REGISTRY_PATH') as f:
    registry = yaml.safe_load(f)

today = date.today()
count = 0
for project, secrets in registry.get('secrets', {}).items():
    if not isinstance(secrets, list):
        continue
    for secret in secrets:
        next_rot = secret.get('next_rotation')
        if next_rot:
            from datetime import datetime
            next_date = datetime.fromisoformat(next_rot).date()
            if (next_date - today).days < 0:
                count += 1
print(count)
" 2>/dev/null || echo "0")

        if [[ "$overdue" =~ ^[0-9]+$ ]] && [[ "$overdue" -gt 0 ]]; then
            log_error "$overdue secrets are overdue for rotation"
            ((issues++))
        else
            log_success "No overdue secrets"
        fi
    fi

    # Check kubectl access
    log_info "Checking Kubernetes access..."
    if kubectl cluster-info &> /dev/null; then
        log_success "Kubernetes cluster accessible"

        # Check secrets exist in namespaces
        for ns in janua enclii; do
            if kubectl get namespace "$ns" &> /dev/null; then
                local secret_count
                secret_count=$(kubectl get secrets -n "$ns" --no-headers 2>/dev/null | wc -l)
                log_info "  $ns namespace: $secret_count secrets"
            fi
        done
    else
        log_warn "Kubernetes cluster not accessible (skip K8s checks)"
    fi

    # Check runbooks exist
    log_info "Checking runbooks..."
    local required_runbooks=("EMERGENCY_ROTATION.md" "oauth-google-rotation.md" "ghcr-pat-rotation.md")
    for runbook in "${required_runbooks[@]}"; do
        if [[ -f "$RUNBOOKS_PATH/$runbook" ]]; then
            log_success "  $runbook exists"
        else
            log_warn "  $runbook missing"
        fi
    done

    # Summary
    echo ""
    if [[ $issues -eq 0 ]]; then
        log_success "Audit complete: No critical issues found"
    else
        log_error "Audit complete: $issues issues found"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Emergency Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_emergency() {
    local critical_only=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --critical) critical_only=true; shift ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
    done

    log_header "EMERGENCY SECRET ROTATION"

    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  WARNING: This will rotate secrets and may cause disruption!   ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Emergency runbook: $RUNBOOKS_PATH/EMERGENCY_ROTATION.md"
    echo ""

    if [[ "$critical_only" == true ]]; then
        log_warn "Critical secrets that would be rotated:"
        echo "  - JWT signing keys (24h grace period)"
        echo "  - Database passwords"
        echo ""
        log_warn "Secrets requiring manual rotation:"
        echo "  - Stripe API keys (rotate in Stripe Dashboard)"
        echo "  - OAuth secrets (rotate in provider consoles)"
    else
        log_info "For emergency rotation, run with explicit confirmation:"
        echo ""
        echo "  # Rotate critical secrets only"
        echo "  ./manage-secrets.sh rotate janua-jwt-private-key"
        echo "  ./manage-secrets.sh rotate janua-postgres-password"
        echo ""
        echo "  # Or see emergency runbook for full procedure"
        echo "  cat $RUNBOOKS_PATH/EMERGENCY_ROTATION.md"
    fi

    echo ""
    read -p "Open emergency runbook? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v open &> /dev/null; then
            open "$RUNBOOKS_PATH/EMERGENCY_ROTATION.md"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$RUNBOOKS_PATH/EMERGENCY_ROTATION.md"
        else
            cat "$RUNBOOKS_PATH/EMERGENCY_ROTATION.md"
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Verify Command
# ═══════════════════════════════════════════════════════════════════════════════

cmd_verify() {
    log_header "Verify Secrets Accessibility"

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    local namespaces=("janua" "enclii")
    local all_ok=true

    for ns in "${namespaces[@]}"; do
        log_info "Checking namespace: $ns"

        if ! kubectl get namespace "$ns" &> /dev/null; then
            log_warn "  Namespace $ns not found, skipping"
            continue
        fi

        # List secrets
        local secrets
        secrets=$(kubectl get secrets -n "$ns" -o name 2>/dev/null)

        for secret in $secrets; do
            local secret_name
            secret_name=$(echo "$secret" | cut -d'/' -f2)

            # Skip service account tokens
            if [[ "$secret_name" == *"token"* ]] || [[ "$secret_name" == "default-"* ]]; then
                continue
            fi

            # Try to read secret
            if kubectl get "$secret" -n "$ns" &> /dev/null; then
                log_success "  $secret_name: accessible"
            else
                log_error "  $secret_name: NOT ACCESSIBLE"
                all_ok=false
            fi
        done
    done

    echo ""
    if [[ "$all_ok" == true ]]; then
        log_success "All secrets verified accessible"
    else
        log_error "Some secrets are not accessible"
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    if [[ $# -lt 1 ]]; then
        show_help
        exit 0
    fi

    local command="$1"
    shift

    case "$command" in
        status)     cmd_status "$@" ;;
        list)       cmd_list "$@" ;;
        rotate)     cmd_rotate "$@" ;;
        update)     cmd_update "$@" ;;
        audit)      cmd_audit "$@" ;;
        emergency)  cmd_emergency "$@" ;;
        verify)     cmd_verify "$@" ;;
        help|--help|-h) show_help ;;
        *)
            log_error "Unknown command: $command"
            echo "Run './manage-secrets.sh help' for usage"
            exit 1
            ;;
    esac
}

main "$@"
