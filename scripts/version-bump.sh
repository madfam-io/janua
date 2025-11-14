#!/bin/bash
# Semantic version bumping for SDK packages
# Usage: ./version-bump.sh <sdk-name> <bump-type> [--dry-run]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
SDK_NAME=""
BUMP_TYPE=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            if [ -z "$SDK_NAME" ]; then
                SDK_NAME="$1"
            elif [ -z "$BUMP_TYPE" ]; then
                BUMP_TYPE="$1"
            else
                echo -e "${RED}❌ Unexpected argument: $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate inputs
if [ -z "$SDK_NAME" ] || [ -z "$BUMP_TYPE" ]; then
    echo "Usage: $0 <sdk-name> <bump-type> [--dry-run]"
    echo ""
    echo "SDKs:"
    echo "  - typescript-sdk, react-sdk, nextjs-sdk, vue-sdk"
    echo "  - python-sdk"
    echo "  - go-sdk"
    echo ""
    echo "Bump types:"
    echo "  - patch    (0.0.X) - Bug fixes"
    echo "  - minor    (0.X.0) - New features (backward compatible)"
    echo "  - major    (X.0.0) - Breaking changes"
    echo "  - premajor (X.0.0-alpha.0)"
    echo "  - preminor (0.X.0-alpha.0)"
    echo "  - prepatch (0.0.X-alpha.0)"
    echo "  - prerelease (increment prerelease)"
    exit 1
fi

# Validate bump type
case "$BUMP_TYPE" in
    patch|minor|major|premajor|preminor|prepatch|prerelease)
        ;;
    *)
        echo -e "${RED}❌ Invalid bump type: $BUMP_TYPE${NC}"
        exit 1
        ;;
esac

# Function to bump NPM package version
bump_npm_version() {
    local SDK_PATH=$1
    local PACKAGE_JSON="$SDK_PATH/package.json"
    
    if [ ! -f "$PACKAGE_JSON" ]; then
        echo -e "${RED}❌ package.json not found: $PACKAGE_JSON${NC}"
        return 1
    fi
    
    # Get current version
    CURRENT_VERSION=$(node -p "require('./$PACKAGE_JSON').version")
    echo -e "${BLUE}Current version: $CURRENT_VERSION${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        # Calculate new version without modifying
        NEW_VERSION=$(npm version "$BUMP_TYPE" --no-git-tag-version --prefix "$SDK_PATH" 2>&1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?' | sed 's/^v//')
        
        # Revert the change
        cd "$SDK_PATH"
        git checkout package.json package-lock.json 2>/dev/null || true
        cd - > /dev/null
        
        echo -e "${YELLOW}Would bump to: $NEW_VERSION${NC}"
    else
        # Bump version
        cd "$SDK_PATH"
        npm version "$BUMP_TYPE" --no-git-tag-version
        NEW_VERSION=$(node -p "require('./package.json').version")
        cd - > /dev/null
        
        echo -e "${GREEN}Bumped to: $NEW_VERSION${NC}"
    fi
}

# Function to bump Python package version
bump_python_version() {
    local SDK_PATH=$1
    local PYPROJECT="$SDK_PATH/pyproject.toml"
    
    if [ ! -f "$PYPROJECT" ]; then
        echo -e "${RED}❌ pyproject.toml not found: $PYPROJECT${NC}"
        return 1
    fi
    
    # Get current version
    CURRENT_VERSION=$(grep '^version = ' "$PYPROJECT" | cut -d'"' -f2)
    echo -e "${BLUE}Current version: $CURRENT_VERSION${NC}"
    
    # Calculate new version using semver logic
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    
    # Handle pre-release versions
    if [[ "$PATCH" =~ ^([0-9]+)(-(.*))?$ ]]; then
        PATCH_NUM="${BASH_REMATCH[1]}"
        PRERELEASE="${BASH_REMATCH[3]}"
    else
        PATCH_NUM="$PATCH"
        PRERELEASE=""
    fi
    
    case "$BUMP_TYPE" in
        patch)
            PATCH_NUM=$((PATCH_NUM + 1))
            PRERELEASE=""
            ;;
        minor)
            MINOR=$((MINOR + 1))
            PATCH_NUM=0
            PRERELEASE=""
            ;;
        major)
            MAJOR=$((MAJOR + 1))
            MINOR=0
            PATCH_NUM=0
            PRERELEASE=""
            ;;
        prepatch)
            PATCH_NUM=$((PATCH_NUM + 1))
            PRERELEASE="alpha.0"
            ;;
        preminor)
            MINOR=$((MINOR + 1))
            PATCH_NUM=0
            PRERELEASE="alpha.0"
            ;;
        premajor)
            MAJOR=$((MAJOR + 1))
            MINOR=0
            PATCH_NUM=0
            PRERELEASE="alpha.0"
            ;;
        prerelease)
            if [ -z "$PRERELEASE" ]; then
                echo -e "${RED}❌ No prerelease to increment${NC}"
                return 1
            fi
            # Increment prerelease number
            IFS='.' read -r PRE_TYPE PRE_NUM <<< "$PRERELEASE"
            PRE_NUM=$((PRE_NUM + 1))
            PRERELEASE="$PRE_TYPE.$PRE_NUM"
            ;;
    esac
    
    if [ -n "$PRERELEASE" ]; then
        NEW_VERSION="$MAJOR.$MINOR.$PATCH_NUM-$PRERELEASE"
    else
        NEW_VERSION="$MAJOR.$MINOR.$PATCH_NUM"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Would bump to: $NEW_VERSION${NC}"
    else
        # Update pyproject.toml
        sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" "$PYPROJECT"
        rm -f "$PYPROJECT.bak"
        echo -e "${GREEN}Bumped to: $NEW_VERSION${NC}"
    fi
}

# Determine SDK type and bump version
echo -e "${BLUE}📊 Bumping version for $SDK_NAME ($BUMP_TYPE)${NC}"
echo ""

case "$SDK_NAME" in
    typescript-sdk|react-sdk|nextjs-sdk|vue-sdk)
        bump_npm_version "packages/$SDK_NAME"
        ;;
    python-sdk)
        bump_python_version "packages/$SDK_NAME"
        ;;
    go-sdk)
        echo -e "${YELLOW}⚠️  Go module versions are managed via git tags${NC}"
        echo -e "${YELLOW}   No version file to update${NC}"
        echo ""
        echo "For Go SDK versioning:"
        echo "  1. Commit your changes"
        echo "  2. Create a tag: git tag -a go-sdk/v1.0.0 -m 'Release v1.0.0'"
        echo "  3. Push the tag: git push origin go-sdk/v1.0.0"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Unknown SDK: $SDK_NAME${NC}"
        exit 1
        ;;
esac

if [ "$DRY_RUN" = false ]; then
    echo ""
    echo -e "${GREEN}✅ Version bumped successfully${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Review the changes: git diff"
    echo "  2. Commit: git add . && git commit -m 'chore: bump $SDK_NAME to $NEW_VERSION'"
    echo "  3. Build: npm run build (for NPM packages)"
    echo "  4. Publish: ./scripts/publish-sdk.sh $SDK_NAME"
fi
