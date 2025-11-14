#!/bin/bash
# Automatic semantic versioning based on conventional commits
# Analyzes commit messages since last tag to determine version bump
# Usage: ./auto-version.sh <sdk-name> [--dry-run]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
SDK_NAME=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            SDK_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$SDK_NAME" ]; then
    echo "Usage: $0 <sdk-name> [--dry-run]"
    echo ""
    echo "Automatically determines version bump based on conventional commits"
    echo "since the last release tag."
    echo ""
    echo "Conventional commit types:"
    echo "  - feat:     → minor bump (new features)"
    echo "  - fix:      → patch bump (bug fixes)"
    echo "  - perf:     → patch bump (performance)"
    echo "  - BREAKING: → major bump (breaking changes)"
    echo "  - build:    → patch bump (build system)"
    echo "  - chore:    → no bump (maintenance)"
    echo "  - docs:     → no bump (documentation)"
    echo "  - style:    → no bump (formatting)"
    echo "  - refactor: → no bump (code restructuring)"
    echo "  - test:     → no bump (tests)"
    exit 1
fi

echo -e "${BLUE}🔍 Analyzing commits for $SDK_NAME${NC}"
echo ""

# Find the latest tag for this SDK
LATEST_TAG=$(git tag -l "${SDK_NAME}-v*" | sort -V | tail -n 1)

if [ -z "$LATEST_TAG" ]; then
    echo -e "${YELLOW}⚠️  No previous tags found for $SDK_NAME${NC}"
    echo -e "${YELLOW}   Assuming initial release${NC}"
    LATEST_TAG=""
    REFERENCE="HEAD"
else
    echo -e "${GREEN}Latest tag: $LATEST_TAG${NC}"
    REFERENCE="$LATEST_TAG..HEAD"
fi

# Get commits since last tag
COMMITS=$(git log "$REFERENCE" --oneline --no-merges 2>/dev/null || echo "")

if [ -z "$COMMITS" ]; then
    echo -e "${YELLOW}⚠️  No new commits since $LATEST_TAG${NC}"
    echo -e "${YELLOW}   Nothing to version${NC}"
    exit 0
fi

echo -e "${BLUE}Commits since last release:${NC}"
echo "$COMMITS"
echo ""

# Analyze commit messages
HAS_BREAKING=false
HAS_FEAT=false
HAS_FIX=false

while IFS= read -r commit; do
    MESSAGE=$(echo "$commit" | cut -d' ' -f2-)
    
    # Check for breaking changes
    if echo "$MESSAGE" | grep -qiE "BREAKING[ -]CHANGE|^[a-z]+!:"; then
        HAS_BREAKING=true
    fi
    
    # Check for features
    if echo "$MESSAGE" | grep -qiE "^feat(\(.+\))?:"; then
        HAS_FEAT=true
    fi
    
    # Check for fixes
    if echo "$MESSAGE" | grep -qiE "^(fix|perf|build)(\(.+\))?:"; then
        HAS_FIX=true
    fi
done <<< "$COMMITS"

# Determine bump type
BUMP_TYPE=""

if [ "$HAS_BREAKING" = true ]; then
    BUMP_TYPE="major"
    echo -e "${RED}🚨 Breaking changes detected → MAJOR bump${NC}"
elif [ "$HAS_FEAT" = true ]; then
    BUMP_TYPE="minor"
    echo -e "${GREEN}✨ New features detected → MINOR bump${NC}"
elif [ "$HAS_FIX" = true ]; then
    BUMP_TYPE="patch"
    echo -e "${BLUE}🐛 Fixes detected → PATCH bump${NC}"
else
    echo -e "${YELLOW}⚠️  No version-worthy changes detected${NC}"
    echo -e "${YELLOW}   Commits contain only chore/docs/style/refactor/test${NC}"
    exit 0
fi

echo ""

# Execute version bump
BUMP_ARGS=("$SDK_NAME" "$BUMP_TYPE")

if [ "$DRY_RUN" = true ]; then
    BUMP_ARGS+=("--dry-run")
fi

./scripts/version-bump.sh "${BUMP_ARGS[@]}"
