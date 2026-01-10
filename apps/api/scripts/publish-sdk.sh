#!/bin/bash
# Unified SDK publishing script
# Usage: ./publish-sdk.sh <sdk-name> [options]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Show help
show_help() {
    echo "Usage: $0 <sdk-name> [options]"
    echo ""
    echo "SDKs:"
    echo "  NPM-based:"
    echo "    - typescript-sdk"
    echo "    - react-sdk"
    echo "    - nextjs-sdk"
    echo "    - vue-sdk"
    echo ""
    echo "  Python:"
    echo "    - python-sdk"
    echo ""
    echo "  Go:"
    echo "    - go-sdk"
    echo ""
    echo "Options:"
    echo "  --dry-run        Run without actually publishing"
    echo "  --tag <tag>      NPM tag (default: latest)"
    echo "  --test-pypi      Publish to Test PyPI (Python only)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 typescript-sdk --dry-run"
    echo "  $0 python-sdk --test-pypi"
    echo "  $0 vue-sdk --tag beta"
}

# Parse SDK name
SDK_NAME=""
ARGS=()

for arg in "$@"; do
    if [ "$arg" = "--help" ]; then
        show_help
        exit 0
    elif [ -z "$SDK_NAME" ] && [[ ! "$arg" =~ ^-- ]]; then
        SDK_NAME="$arg"
    else
        ARGS+=("$arg")
    fi
done

if [ -z "$SDK_NAME" ]; then
    echo -e "${RED}❌ SDK name required${NC}"
    echo ""
    show_help
    exit 1
fi

# Determine SDK type and delegate to appropriate script
case "$SDK_NAME" in
    typescript-sdk|react-sdk|nextjs-sdk|vue-sdk)
        echo -e "${BLUE}Publishing NPM SDK: $SDK_NAME${NC}"
        exec ./scripts/publish-npm-sdk.sh "$SDK_NAME" "${ARGS[@]}"
        ;;
    python-sdk)
        echo -e "${BLUE}Publishing Python SDK${NC}"
        exec ./scripts/publish-python-sdk.sh "${ARGS[@]}"
        ;;
    go-sdk)
        echo -e "${YELLOW}⚠️  Go SDK publishing${NC}"
        echo ""
        echo "Go modules are published via git tags, not package registries."
        echo ""
        echo "To publish the Go SDK:"
        echo "  1. Ensure all changes are committed"
        echo "  2. Create and push a version tag:"
        echo "     git tag -a go-sdk/v1.0.0 -m 'Release v1.0.0'"
        echo "     git push origin go-sdk/v1.0.0"
        echo ""
        echo "Users can then install with:"
        echo "  go get github.com/madfam-org/janua/packages/go-sdk@v1.0.0"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Unknown SDK: $SDK_NAME${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
