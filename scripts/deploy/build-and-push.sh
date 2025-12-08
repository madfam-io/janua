#!/bin/bash
# Janua Local Build and Deploy Script
# Usage: ./build-and-push.sh [service] [--push] [--deploy]
#
# Services: api, dashboard, admin, docs, website, all
#
# Examples:
#   ./build-and-push.sh api              # Build API image only
#   ./build-and-push.sh api --push       # Build and push to server registry
#   ./build-and-push.sh api --deploy     # Build, push, and deploy to K8s
#   ./build-and-push.sh all --deploy     # Build and deploy all services

set -e

# Configuration
REGISTRY="localhost:5000"
SSH_HOST="ssh.madfam.io"
NAMESPACE="janua"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get dockerfile for service
get_dockerfile() {
    case "$1" in
        api) echo "Dockerfile.api" ;;
        dashboard) echo "Dockerfile.dashboard" ;;
        admin) echo "Dockerfile.admin" ;;
        docs) echo "Dockerfile.docs" ;;
        website) echo "Dockerfile.website" ;;
        *) echo "" ;;
    esac
}

# Get deployment name for service
get_deployment() {
    case "$1" in
        api) echo "janua-api" ;;
        dashboard) echo "janua-dashboard" ;;
        admin) echo "janua-admin" ;;
        docs) echo "janua-docs" ;;
        website) echo "janua-website" ;;
        *) echo "" ;;
    esac
}

build_service() {
    local service="$1"
    local dockerfile
    dockerfile=$(get_dockerfile "$service")
    local tag="${REGISTRY}/janua-${service}:latest"

    if [[ -z "$dockerfile" ]]; then
        log_error "Unknown service: $service"
        return 1
    fi

    if [[ ! -f "$REPO_ROOT/$dockerfile" ]]; then
        log_error "Dockerfile not found: $dockerfile"
        return 1
    fi

    log_info "Building $service from $dockerfile..."
    docker build -t "$tag" -f "$REPO_ROOT/$dockerfile" "$REPO_ROOT"

    log_info "Built: $tag"
}

push_service() {
    local service="$1"
    local tag="${REGISTRY}/janua-${service}:latest"

    log_info "Pushing $tag to server registry..."

    # Save image to tar
    local tar_file="/tmp/janua-${service}.tar"
    docker save "$tag" > "$tar_file"

    # Transfer to server
    scp "$tar_file" "${SSH_HOST}:/tmp/"

    # Load into server's registry
    ssh "$SSH_HOST" "docker load < /tmp/janua-${service}.tar && \
        docker tag $tag localhost:5000/janua-${service}:latest && \
        docker push localhost:5000/janua-${service}:latest && \
        rm /tmp/janua-${service}.tar"

    rm "$tar_file"
    log_info "Pushed: $tag"
}

deploy_service() {
    local service="$1"
    local deployment
    deployment=$(get_deployment "$service")
    local tag="localhost:5000/janua-${service}:latest"

    log_info "Deploying $deployment..."

    ssh "$SSH_HOST" "sudo kubectl set image deployment/$deployment $deployment=$tag -n $NAMESPACE && \
        sudo kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=120s"

    log_info "Deployed: $deployment"
}

show_help() {
    cat <<EOF
Janua Local Build and Deploy Script

Usage: $0 <service> [options]

Services:
  api         Build API service
  dashboard   Build Dashboard service
  admin       Build Admin service
  docs        Build Documentation service
  website     Build Website service
  all         Build all services

Options:
  --push      Push images to server registry after build
  --deploy    Deploy to K8s after push (implies --push)
  --help      Show this help message

Examples:
  $0 api                   # Build API image only
  $0 api --push            # Build and push to server
  $0 api --deploy          # Build, push, and deploy
  $0 all --deploy          # Build and deploy all services
EOF
}

# Parse arguments
SERVICE=""
DO_PUSH=false
DO_DEPLOY=false

for arg in "$@"; do
    case "$arg" in
        --push)
            DO_PUSH=true
            ;;
        --deploy)
            DO_PUSH=true
            DO_DEPLOY=true
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            SERVICE="$arg"
            ;;
    esac
done

if [[ -z "$SERVICE" ]]; then
    log_error "Service name required"
    show_help
    exit 1
fi

# Determine which services to build
if [[ "$SERVICE" == "all" ]]; then
    SERVICES="api dashboard admin docs website"
else
    SERVICES="$SERVICE"
fi

# Execute
for svc in $SERVICES; do
    log_info "Processing $svc..."

    build_service "$svc"

    if $DO_PUSH; then
        push_service "$svc"
    fi

    if $DO_DEPLOY; then
        deploy_service "$svc"
    fi

    echo ""
done

log_info "Done!"
