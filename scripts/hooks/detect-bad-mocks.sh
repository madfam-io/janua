#!/bin/bash
# Detect incorrect mock paths that will silently fail
# These patterns cause mocks to not be applied, leading to real HTTP calls in tests

set -euo pipefail

ERRORS=0
WARNINGS=0

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "Checking for incorrect mock paths..."

# If no files provided, exit successfully
if [ $# -eq 0 ]; then
    echo "No files to check"
    exit 0
fi

# Pattern 1: Bare httpx.AsyncClient (should be module.httpx.AsyncClient)
# This pattern doesn't work because patch() needs the path where the name is looked up
BAD_HTTPX=$(grep -rn 'patch("httpx\.' "$@" 2>/dev/null || true)
if [ -n "$BAD_HTTPX" ]; then
    echo -e "${RED}ERROR: Found 'patch(\"httpx.*\")' - mock path should be module-specific${NC}"
    echo "$BAD_HTTPX"
    echo ""
    echo "  FIX: Use 'patch(\"app.module.httpx.AsyncClient\")' or 'patch.object()'"
    echo "  Example: patch(\"app.services.oauth.httpx.AsyncClient\")"
    echo ""
    ERRORS=$((ERRORS + 1))
fi

# Pattern 2: Bare requests.Session or requests.get/post
BAD_REQUESTS=$(grep -rn 'patch("requests\.' "$@" 2>/dev/null || true)
if [ -n "$BAD_REQUESTS" ]; then
    echo -e "${RED}ERROR: Found 'patch(\"requests.*\")' - mock path should be module-specific${NC}"
    echo "$BAD_REQUESTS"
    echo ""
    echo "  FIX: Use 'patch(\"app.module.requests.Session\")'"
    echo ""
    ERRORS=$((ERRORS + 1))
fi

# Pattern 3: Bare aiohttp patching
BAD_AIOHTTP=$(grep -rn 'patch("aiohttp\.' "$@" 2>/dev/null || true)
if [ -n "$BAD_AIOHTTP" ]; then
    echo -e "${RED}ERROR: Found 'patch(\"aiohttp.*\")' - mock path should be module-specific${NC}"
    echo "$BAD_AIOHTTP"
    echo ""
    ERRORS=$((ERRORS + 1))
fi

# Warning patterns (not blocking, but worth reviewing)

# Pattern 4: Mocking datetime.datetime directly (common issue)
BAD_DATETIME=$(grep -rn 'patch("datetime\.datetime' "$@" 2>/dev/null || true)
if [ -n "$BAD_DATETIME" ]; then
    echo -e "${YELLOW}WARNING: Found 'patch(\"datetime.datetime\")' - consider module-specific path${NC}"
    echo "$BAD_DATETIME"
    echo "  Consider using 'freezegun' library or module-specific datetime patching"
    echo ""
    WARNINGS=$((WARNINGS + 1))
fi

# Summary
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Found $ERRORS error(s) in mock paths${NC}"
    echo "These patterns cause mocks to not be applied, leading to real HTTP calls in tests."
    exit 1
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Found $WARNINGS warning(s) - please review${NC}"
fi

echo "Mock paths check passed"
exit 0
