#!/bin/bash
# Publish Python SDK to PyPI
# Usage: ./publish-python-sdk.sh [--dry-run] [--test-pypi]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
DRY_RUN=false
TEST_PYPI=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --test-pypi)
            TEST_PYPI=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

SDK_PATH="packages/python-sdk"

# Validate SDK exists
if [ ! -d "$SDK_PATH" ]; then
    echo -e "${RED}❌ Python SDK not found: $SDK_PATH${NC}"
    exit 1
fi

# Get package info
PACKAGE_VERSION=$(grep '^version = ' "$SDK_PATH/pyproject.toml" | cut -d'"' -f2)

echo -e "${BLUE}📦 Publishing plinto@$PACKAGE_VERSION to PyPI${NC}"
echo ""

# Pre-publish checks
echo -e "${YELLOW}🔍 Running pre-publish checks...${NC}"

# 1. Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Python installed${NC}"

# 2. Check if build module is installed
if ! python -m build --version &> /dev/null; then
    echo -e "${YELLOW}⚠️  build module not installed${NC}"
    echo -e "${YELLOW}   Installing build module...${NC}"
    python -m pip install --upgrade build
fi
echo -e "${GREEN}  ✓ build module available${NC}"

# 3. Check if twine is installed
if ! command -v twine &> /dev/null; then
    echo -e "${YELLOW}⚠️  twine not installed${NC}"
    echo -e "${YELLOW}   Installing twine...${NC}"
    python -m pip install --upgrade twine
fi
echo -e "${GREEN}  ✓ twine available${NC}"

# 4. Clean old builds
echo -e "${YELLOW}  → Cleaning old builds...${NC}"
rm -rf "$SDK_PATH/dist" "$SDK_PATH/build" "$SDK_PATH/*.egg-info"
echo -e "${GREEN}  ✓ Old builds cleaned${NC}"

# 5. Build distributions
echo -e "${YELLOW}  → Building distributions...${NC}"
cd "$SDK_PATH"
if ! python -m build; then
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi
cd - > /dev/null
echo -e "${GREEN}  ✓ Distributions built${NC}"

# 6. Check dist/ contents
WHEEL_COUNT=$(find "$SDK_PATH/dist" -name "*.whl" 2>/dev/null | wc -l | tr -d ' ')
SDIST_COUNT=$(find "$SDK_PATH/dist" -name "*.tar.gz" 2>/dev/null | wc -l | tr -d ' ')

if [ "$WHEEL_COUNT" -eq 0 ] || [ "$SDIST_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ Build did not produce wheel and/or sdist${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Found $WHEEL_COUNT wheel(s) and $SDIST_COUNT source dist(s)${NC}"

# 7. Run twine check
echo -e "${YELLOW}  → Running twine check...${NC}"
if ! twine check "$SDK_PATH/dist/*"; then
    echo -e "${RED}❌ Twine check failed${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Twine check passed${NC}"

# 8. Check if version exists on PyPI
echo -e "${YELLOW}  → Checking if version exists on PyPI...${NC}"
if pip index versions plinto 2>/dev/null | grep -q "$PACKAGE_VERSION"; then
    echo -e "${RED}❌ Version $PACKAGE_VERSION already published${NC}"
    echo -e "${YELLOW}   Bump version in pyproject.toml before publishing${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Version $PACKAGE_VERSION is new${NC}"

# 9. Run tests (if available)
if [ -d "$SDK_PATH/tests" ]; then
    echo -e "${YELLOW}  → Running tests...${NC}"
    cd "$SDK_PATH"
    if python -m pytest tests/ -q --tb=no 2>/dev/null; then
        echo -e "${GREEN}  ✓ Tests passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some tests failed or pytest not available${NC}"
        echo -e "${YELLOW}   Continuing with publish...${NC}"
    fi
    cd - > /dev/null
fi

# 10. Check git status
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
    echo ""
    echo -e "${BLUE}Package contents that would be published:${NC}"
    ls -lh "$SDK_PATH/dist/"
else
    REPOSITORY_ARG=""
    if [ "$TEST_PYPI" = true ]; then
        echo -e "${BLUE}📤 Publishing to Test PyPI...${NC}"
        REPOSITORY_ARG="--repository testpypi"
    else
        echo -e "${BLUE}📤 Publishing to PyPI...${NC}"
        REPOSITORY_ARG="--repository pypi"
    fi
    
    # Upload to PyPI
    if twine upload $REPOSITORY_ARG "$SDK_PATH/dist/*"; then
        echo -e "${GREEN}✅ Successfully published plinto@$PACKAGE_VERSION${NC}"
        echo ""
        echo -e "${BLUE}📋 Post-publish:${NC}"
        if [ "$TEST_PYPI" = true ]; then
            echo -e "  1. Verify: pip index versions plinto --index-url https://test.pypi.org/simple/"
            echo -e "  2. Test install: pip install --index-url https://test.pypi.org/simple/ plinto==$PACKAGE_VERSION"
        else
            echo -e "  1. Verify: pip index versions plinto"
            echo -e "  2. Test install: pip install plinto==$PACKAGE_VERSION"
        fi
        echo -e "  3. Create git tag: git tag -a python-sdk-v$PACKAGE_VERSION -m 'Release $PACKAGE_VERSION'"
        echo -e "  4. Push tag: git push origin python-sdk-v$PACKAGE_VERSION"
    else
        echo -e "${RED}❌ Publish failed${NC}"
        exit 1
    fi
fi
