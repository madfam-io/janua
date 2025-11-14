#!/bin/bash
# Publish NPM-based SDK to registry
# Usage: ./publish-npm-sdk.sh <sdk-name> [--dry-run] [--tag <tag>]

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
NPM_TAG="latest"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --tag)
            NPM_TAG="$2"
            shift 2
            ;;
        *)
            SDK_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$SDK_NAME" ]; then
    echo -e "${RED}❌ SDK name required${NC}"
    echo "Usage: $0 <sdk-name> [--dry-run] [--tag <tag>]"
    echo ""
    echo "Available SDKs:"
    echo "  - typescript-sdk"
    echo "  - react-sdk"
    echo "  - nextjs-sdk"
    echo "  - vue-sdk"
    exit 1
fi

SDK_PATH="packages/$SDK_NAME"

# Validate SDK exists
if [ ! -d "$SDK_PATH" ]; then
    echo -e "${RED}❌ SDK not found: $SDK_PATH${NC}"
    exit 1
fi

if [ ! -f "$SDK_PATH/package.json" ]; then
    echo -e "${RED}❌ package.json not found in $SDK_PATH${NC}"
    exit 1
fi

# Get package info
PACKAGE_NAME=$(node -p "require('./$SDK_PATH/package.json').name")
PACKAGE_VERSION=$(node -p "require('./$SDK_PATH/package.json').version")

echo -e "${BLUE}📦 Publishing $PACKAGE_NAME@$PACKAGE_VERSION${NC}"
echo ""

# Pre-publish checks
echo -e "${YELLOW}🔍 Running pre-publish checks...${NC}"

# 1. Check if dist/ exists
if [ ! -d "$SDK_PATH/dist" ]; then
    echo -e "${RED}❌ dist/ directory not found${NC}"
    echo -e "${YELLOW}   Run 'npm run build' in $SDK_PATH first${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ dist/ directory exists${NC}"

# 2. Check if dist/ has files
DIST_FILES=$(find "$SDK_PATH/dist" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$DIST_FILES" -eq 0 ]; then
    echo -e "${RED}❌ dist/ directory is empty${NC}"
    echo -e "${YELLOW}   Run 'npm run build' in $SDK_PATH first${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ dist/ contains $DIST_FILES files${NC}"

# 3. Run tests (if test script exists)
if grep -q '"test"' "$SDK_PATH/package.json"; then
    echo -e "${YELLOW}  → Running tests...${NC}"
    if ! npm test --prefix "$SDK_PATH" --silent; then
        echo -e "${RED}❌ Tests failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Tests passed${NC}"
fi

# 4. Run linter (if lint script exists)
if grep -q '"lint"' "$SDK_PATH/package.json"; then
    echo -e "${YELLOW}  → Running linter...${NC}"
    if ! npm run lint --prefix "$SDK_PATH" --silent; then
        echo -e "${RED}❌ Linter failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Lint passed${NC}"
fi

# 5. Run typecheck (if typecheck script exists)
if grep -q '"typecheck"' "$SDK_PATH/package.json"; then
    echo -e "${YELLOW}  → Running typecheck...${NC}"
    if ! npm run typecheck --prefix "$SDK_PATH" --silent; then
        echo -e "${RED}❌ Typecheck failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Typecheck passed${NC}"
fi

# 6. Check if version already exists on NPM
echo -e "${YELLOW}  → Checking if version exists on NPM...${NC}"
if npm view "$PACKAGE_NAME@$PACKAGE_VERSION" version 2>/dev/null; then
    echo -e "${RED}❌ Version $PACKAGE_VERSION already published${NC}"
    echo -e "${YELLOW}   Bump version in package.json before publishing${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Version $PACKAGE_VERSION is new${NC}"

# 7. Check git status
echo -e "${YELLOW}  → Checking git status...${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Uncommitted changes detected${NC}"
    echo -e "${YELLOW}   Consider committing changes before publishing${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Publish cancelled${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}  ✓ Git status checked${NC}"

echo ""
echo -e "${GREEN}✅ All pre-publish checks passed${NC}"
echo ""

# Publish
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}🏃 DRY RUN MODE - No actual publish${NC}"
    echo -e "${YELLOW}Would run: npm publish $SDK_PATH --tag $NPM_TAG --access public${NC}"
    echo ""
    echo -e "${BLUE}Package contents that would be published:${NC}"
    npm pack "$SDK_PATH" --dry-run
else
    echo -e "${BLUE}📤 Publishing to NPM...${NC}"
    
    # Publish with public access (for scoped packages)
    if npm publish "$SDK_PATH" --tag "$NPM_TAG" --access public; then
        echo -e "${GREEN}✅ Successfully published $PACKAGE_NAME@$PACKAGE_VERSION${NC}"
        echo ""
        echo -e "${BLUE}📋 Post-publish:${NC}"
        echo -e "  1. Verify: npm view $PACKAGE_NAME@$PACKAGE_VERSION"
        echo -e "  2. Test install: npm install $PACKAGE_NAME@$PACKAGE_VERSION"
        echo -e "  3. Create git tag: git tag -a $SDK_NAME-v$PACKAGE_VERSION -m 'Release $PACKAGE_VERSION'"
        echo -e "  4. Push tag: git push origin $SDK_NAME-v$PACKAGE_VERSION"
    else
        echo -e "${RED}❌ Publish failed${NC}"
        exit 1
    fi
fi
