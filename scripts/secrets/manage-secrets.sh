#!/bin/bash
# Janua Secrets Management Script
# Usage: ./manage-secrets.sh [command] [options]
#
# Commands:
#   export    - Export secrets from K8s to local files (encrypted)
#   import    - Import secrets from local files to K8s
#   generate  - Generate new secrets
#   rotate    - Rotate specified secrets
#   list      - List all secrets in K8s
#   verify    - Verify secrets are properly configured

set -e

# Check for required tools
check_requirements() {
    local cmd="$1"

    # Commands that require jq
    case "$cmd" in
        export|import)
            if ! command -v jq &>/dev/null; then
                echo -e "\033[0;31m[ERROR]\033[0m The '$cmd' command requires 'jq' (brew install jq or apt install jq)"
                exit 1
            fi
            ;;
    esac
}

# Configuration
NAMESPACE="${NAMESPACE:-janua}"
SECRET_NAME="${SECRET_NAME:-janua-secrets}"
SECRETS_DIR="${SECRETS_DIR:-$HOME/.janua-secrets}"
SSH_HOST="${SSH_HOST:-ssh.madfam.io}"
GPG_RECIPIENT="${GPG_RECIPIENT:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse global flags
REMOTE="false"
parse_global_flags() {
    for arg in "$@"; do
        case "$arg" in
            --remote)
                REMOTE="true"
                ;;
        esac
    done
}

# Execute kubectl command (local or remote)
kubectl_cmd() {
    if [[ "$REMOTE" == "true" ]]; then
        ssh "$SSH_HOST" "sudo kubectl $*"
    else
        kubectl "$@"
    fi
}

# List all secrets
cmd_list() {
    log_info "Listing secrets in namespace: $NAMESPACE"
    kubectl_cmd get secrets -n "$NAMESPACE" -o wide
}

# Export secrets to local encrypted files
cmd_export() {
    log_info "Exporting secrets from K8s..."

    # Create secrets directory
    mkdir -p "$SECRETS_DIR"
    chmod 700 "$SECRETS_DIR"

    # Get secret data
    local secret_data
    secret_data=$(kubectl_cmd get secret "$SECRET_NAME" -n "$NAMESPACE" -o json 2>/dev/null)

    if [[ -z "$secret_data" ]]; then
        log_error "Failed to get secret $SECRET_NAME from namespace $NAMESPACE"
        exit 1
    fi

    # Export each key
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local export_file="$SECRETS_DIR/${SECRET_NAME}_${timestamp}.json"

    echo "$secret_data" | jq '.data | to_entries | map({(.key): (.value | @base64d)}) | add' > "$export_file"
    chmod 600 "$export_file"

    # Optionally encrypt with GPG
    if [[ -n "$GPG_RECIPIENT" ]]; then
        gpg --encrypt --recipient "$GPG_RECIPIENT" "$export_file"
        rm "$export_file"
        export_file="${export_file}.gpg"
    fi

    log_info "Secrets exported to: $export_file"
}

# Import secrets from local file to K8s
cmd_import() {
    local import_file="$1"

    if [[ -z "$import_file" ]]; then
        log_error "Usage: $0 import <secrets-file.json>"
        exit 1
    fi

    if [[ ! -f "$import_file" ]]; then
        log_error "File not found: $import_file"
        exit 1
    fi

    log_info "Importing secrets from: $import_file"

    # Decrypt if encrypted
    local json_file="$import_file"
    if [[ "$import_file" == *.gpg ]]; then
        json_file="${import_file%.gpg}"
        gpg --decrypt "$import_file" > "$json_file"
    fi

    # Read and encode secrets
    local secret_yaml
    secret_yaml=$(cat <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: $SECRET_NAME
  namespace: $NAMESPACE
type: Opaque
data:
$(jq -r 'to_entries | map("  \(.key): \(.value | @base64)") | .[]' "$json_file")
EOF
)

    # Apply to K8s
    echo "$secret_yaml" | kubectl_cmd apply -f -

    # Cleanup decrypted file if we decrypted it
    if [[ "$import_file" == *.gpg ]]; then
        rm "$json_file"
    fi

    log_info "Secrets imported successfully"
}

# Generate new secrets
cmd_generate() {
    log_info "Generating new secrets..."

    local jwt_secret=$(openssl rand -base64 32)
    local secret_key=$(openssl rand -base64 32)
    local api_key=$(openssl rand -hex 32)

    echo ""
    echo "Generated secrets:"
    echo "=================="
    echo "jwt-secret:       $jwt_secret"
    echo "secret-key:       $secret_key"
    echo "internal-api-key: $api_key"
    echo ""

    log_warn "These secrets need to be added to your secrets file manually"
    log_warn "Database and Redis URLs need to be configured separately"
}

# Rotate specific secrets
cmd_rotate() {
    local key="$1"

    if [[ -z "$key" ]]; then
        log_error "Usage: $0 rotate <secret-key>"
        log_info "Available keys: jwt-secret, secret-key, internal-api-key"
        exit 1
    fi

    log_info "Rotating secret: $key"

    local new_value
    case "$key" in
        jwt-secret|secret-key)
            new_value=$(openssl rand -base64 32)
            ;;
        internal-api-key)
            new_value=$(openssl rand -hex 32)
            ;;
        *)
            log_error "Unknown secret key: $key"
            exit 1
            ;;
    esac

    # Update in K8s
    local encoded_value
    encoded_value=$(echo -n "$new_value" | base64)

    kubectl_cmd patch secret "$SECRET_NAME" -n "$NAMESPACE" \
        --type='json' \
        -p="[{\"op\": \"replace\", \"path\": \"/data/$key\", \"value\":\"$encoded_value\"}]"

    log_info "Secret $key rotated successfully"
    log_warn "Remember to restart pods to pick up new secret: kubectl rollout restart deployment/janua-api -n $NAMESPACE"
}

# Verify secrets are configured correctly
cmd_verify() {
    log_info "Verifying secrets configuration..."

    local required_keys=("database-url" "jwt-secret" "secret-key" "redis-url")
    local missing=()

    # Get secret keys using kubectl jsonpath and parse with grep (no jq dependency)
    local secret_data
    secret_data=$(kubectl_cmd get secret "$SECRET_NAME" -n "$NAMESPACE" -o "jsonpath={.data}" 2>/dev/null)

    # Extract keys from JSON using grep/sed (works without jq)
    local secret_keys
    secret_keys=$(echo "$secret_data" | grep -oE '"[^"]+":' | tr -d '":' | sort)

    for key in "${required_keys[@]}"; do
        if ! echo "$secret_keys" | grep -q "^$key$"; then
            missing+=("$key")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required secrets: ${missing[*]}"
        exit 1
    fi

    log_info "All required secrets are present"

    # Check if secrets are being used by pods
    # Note: This is a simplified check - pods may use secrets via envFrom or volume mounts
    log_info "Checking pods in namespace..."
    local pods
    pods=$(kubectl_cmd get pods -n "$NAMESPACE" -o name 2>/dev/null | sed 's/pod\///')

    if [[ -z "$pods" ]]; then
        log_warn "No pods found in namespace $NAMESPACE"
    else
        log_info "Pods in namespace (secrets may be used via envFrom or volumes):"
        echo "$pods"
    fi
}

# Template for .env file
cmd_template() {
    cat <<'EOF'
# Janua API Environment Variables Template
# Copy this to .env and fill in values

# Database Configuration
DATABASE_URL=postgresql://janua:PASSWORD@localhost:5432/janua
REDIS_URL=redis://localhost:6379

# Security Keys (generate with: openssl rand -base64 32)
JWT_SECRET=
SECRET_KEY=
INTERNAL_API_KEY=

# Email Provider (resend, ses, smtp, sendgrid)
EMAIL_PROVIDER=resend
RESEND_API_KEY=

# OAuth Providers (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=info
CORS_ORIGINS=https://app.janua.dev,https://admin.janua.dev
EOF
}

# Help
cmd_help() {
    cat <<EOF
Janua Secrets Management Script

Usage: $0 <command> [options]

Commands:
  list        List all secrets in K8s namespace
  export      Export secrets to local encrypted file
  import      Import secrets from file to K8s
  generate    Generate new secret values
  rotate      Rotate a specific secret
  verify      Verify all required secrets are present
  template    Print .env template

Options:
  --remote    Execute against remote K8s cluster via SSH tunnel
  --namespace Set namespace (default: janua)
  --secret    Set secret name (default: janua-secrets)

Environment Variables:
  NAMESPACE       K8s namespace (default: janua)
  SECRET_NAME     K8s secret name (default: janua-secrets)
  SECRETS_DIR     Local directory for exported secrets
  SSH_HOST        SSH host for remote operations
  GPG_RECIPIENT   GPG recipient for encryption

Examples:
  $0 list --remote
  $0 export
  $0 import secrets.json
  $0 rotate jwt-secret
  $0 verify
EOF
}

# Parse global flags first from all arguments
parse_global_flags "$@"

# Parse command
cmd="${1:-help}"
shift || true

# Check requirements for the command
check_requirements "$cmd"

case "$cmd" in
    list)
        cmd_list "$@"
        ;;
    export)
        cmd_export "$@"
        ;;
    import)
        cmd_import "$@"
        ;;
    generate)
        cmd_generate "$@"
        ;;
    rotate)
        cmd_rotate "$@"
        ;;
    verify)
        cmd_verify "$@"
        ;;
    template)
        cmd_template "$@"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        log_error "Unknown command: $cmd"
        cmd_help
        exit 1
        ;;
esac
