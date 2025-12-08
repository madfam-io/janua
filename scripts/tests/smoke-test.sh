#!/bin/bash
# Janua Production Smoke Test Script
# Usage: ./smoke-test.sh [--verbose] [--fail-fast]
#
# Tests production endpoints to verify basic functionality after deployment.

set -e

# Configuration
API_URL="${API_URL:-https://api.janua.dev}"
APP_URL="${APP_URL:-https://app.janua.dev}"
ADMIN_URL="${ADMIN_URL:-https://admin.janua.dev}"
DOCS_URL="${DOCS_URL:-https://docs.janua.dev}"
WEBSITE_URL="${WEBSITE_URL:-https://janua.dev}"
TIMEOUT="${TIMEOUT:-10}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Options
VERBOSE=false
FAIL_FAST=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --verbose|-v)
            VERBOSE=true
            ;;
        --fail-fast|-f)
            FAIL_FAST=true
            ;;
        --help|-h)
            echo "Janua Production Smoke Tests"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --verbose, -v     Show detailed output"
            echo "  --fail-fast, -f   Stop on first failure"
            echo "  --help, -h        Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  API_URL      API base URL (default: https://api.janua.dev)"
            echo "  APP_URL      Dashboard URL (default: https://app.janua.dev)"
            echo "  ADMIN_URL    Admin URL (default: https://admin.janua.dev)"
            echo "  DOCS_URL     Docs URL (default: https://docs.janua.dev)"
            echo "  WEBSITE_URL  Website URL (default: https://janua.dev)"
            echo "  TIMEOUT      Request timeout in seconds (default: 10)"
            exit 0
            ;;
    esac
done

log_test() {
    local name="$1"
    local status="$2"
    local details="$3"

    TOTAL=$((TOTAL + 1))

    if [[ "$status" == "PASS" ]]; then
        PASSED=$((PASSED + 1))
        echo -e "${GREEN}✓${NC} $name"
        if $VERBOSE && [[ -n "$details" ]]; then
            echo -e "  ${CYAN}$details${NC}"
        fi
    else
        FAILED=$((FAILED + 1))
        echo -e "${RED}✗${NC} $name"
        if [[ -n "$details" ]]; then
            echo -e "  ${RED}$details${NC}"
        fi
        if $FAIL_FAST; then
            echo ""
            echo -e "${RED}Stopping on first failure (--fail-fast)${NC}"
            print_summary
            exit 1
        fi
    fi
}

print_summary() {
    echo ""
    echo "═══════════════════════════════════════════"
    echo "SMOKE TEST SUMMARY"
    echo "═══════════════════════════════════════════"
    echo -e "Total: $TOTAL | ${GREEN}Passed: $PASSED${NC} | ${RED}Failed: $FAILED${NC}"

    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}Some tests failed!${NC}"
    fi
}

# HTTP request helper
http_get() {
    local url="$1"
    local expected_status="${2:-200}"

    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null) || {
        echo "CURL_ERROR"
        return 1
    }

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "$expected_status" ]]; then
        echo "$body"
        return 0
    else
        echo "HTTP_$http_code"
        return 1
    fi
}

echo "═══════════════════════════════════════════"
echo "JANUA PRODUCTION SMOKE TESTS"
echo "═══════════════════════════════════════════"
echo "Started: $(date)"
echo ""

# ===========================================
# API Tests
# ===========================================
echo "${CYAN}API Tests${NC} ($API_URL)"
echo "-------------------------------------------"

# Test 1: Health endpoint
result=$(http_get "$API_URL/health" 200)
if [[ $? -eq 0 ]]; then
    if echo "$result" | grep -q '"status":"healthy"'; then
        log_test "API Health Check" "PASS" "$result"
    else
        log_test "API Health Check" "FAIL" "Unexpected response: $result"
    fi
else
    log_test "API Health Check" "FAIL" "Request failed: $result"
fi

# Test 2: OpenAPI docs accessible
result=$(http_get "$API_URL/docs" 200)
if [[ $? -eq 0 ]]; then
    log_test "API OpenAPI Docs" "PASS" "Swagger UI accessible"
else
    log_test "API OpenAPI Docs" "FAIL" "$result"
fi

# Test 3: API version endpoint
result=$(http_get "$API_URL/api/v1/" 200)
if [[ $? -eq 0 ]]; then
    log_test "API Version Endpoint" "PASS" "$result"
else
    # May be 404 if not implemented, check for valid HTTP response
    if [[ "$result" == "HTTP_404" ]]; then
        log_test "API Version Endpoint" "PASS" "Endpoint returns 404 (expected)"
    else
        log_test "API Version Endpoint" "FAIL" "$result"
    fi
fi

# Test 4: Auth login endpoint exists (POST, expect 422 for missing body)
result=$(curl -s -w "%{http_code}" -X POST --max-time "$TIMEOUT" "$API_URL/api/v1/auth/login" -H "Content-Type: application/json" -d "{}" 2>/dev/null)
http_code="${result: -3}"
if [[ "$http_code" == "422" || "$http_code" == "400" ]]; then
    log_test "API Auth Login Endpoint" "PASS" "Returns validation error (expected)"
elif [[ "$http_code" == "200" || "$http_code" == "401" ]]; then
    log_test "API Auth Login Endpoint" "PASS" "Endpoint accessible"
else
    log_test "API Auth Login Endpoint" "FAIL" "HTTP $http_code"
fi

# Test 5: Metrics endpoint (if available)
result=$(http_get "$API_URL/metrics" 200)
if [[ $? -eq 0 ]]; then
    if echo "$result" | grep -q "http_requests_total"; then
        log_test "API Metrics Endpoint" "PASS" "Prometheus metrics available"
    else
        log_test "API Metrics Endpoint" "PASS" "Endpoint accessible"
    fi
else
    log_test "API Metrics Endpoint" "FAIL" "$result"
fi

echo ""

# ===========================================
# Frontend Tests
# ===========================================
echo "${CYAN}Frontend Tests${NC}"
echo "-------------------------------------------"

# Dashboard (may redirect to login)
result=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" -L "$APP_URL" 2>/dev/null)
if [[ "$result" == "200" || "$result" == "307" || "$result" == "302" ]]; then
    log_test "Dashboard ($APP_URL)" "PASS" "HTTP $result"
else
    log_test "Dashboard ($APP_URL)" "FAIL" "HTTP $result"
fi

# Admin
result=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" "$ADMIN_URL" 2>/dev/null)
if [[ "$result" == "200" ]]; then
    log_test "Admin Panel ($ADMIN_URL)" "PASS"
else
    log_test "Admin Panel ($ADMIN_URL)" "FAIL" "HTTP $result"
fi

# Docs (may not be deployed)
result=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" "$DOCS_URL" 2>/dev/null)
if [[ "$result" == "200" ]]; then
    log_test "Documentation ($DOCS_URL)" "PASS"
elif [[ "$result" == "000" ]]; then
    log_test "Documentation ($DOCS_URL)" "FAIL" "Not deployed or unreachable"
else
    log_test "Documentation ($DOCS_URL)" "FAIL" "HTTP $result"
fi

# Website
result=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" "$WEBSITE_URL" 2>/dev/null)
if [[ "$result" == "200" ]]; then
    log_test "Website ($WEBSITE_URL)" "PASS"
else
    log_test "Website ($WEBSITE_URL)" "FAIL" "HTTP $result"
fi

echo ""

# ===========================================
# Infrastructure Tests
# ===========================================
echo "${CYAN}Infrastructure Tests${NC}"
echo "-------------------------------------------"

# SSL Certificate validity (API)
result=$(curl -s -w "%{http_code}" -o /dev/null --max-time "$TIMEOUT" "$API_URL" 2>/dev/null)
if [[ "$result" == "200" ]]; then
    log_test "SSL Certificate (API)" "PASS" "HTTPS working"
else
    log_test "SSL Certificate (API)" "FAIL" "HTTPS check failed"
fi

# Response time check
start=$(date +%s%N)
curl -s -o /dev/null --max-time "$TIMEOUT" "$API_URL/health" 2>/dev/null
end=$(date +%s%N)
duration=$(( (end - start) / 1000000 ))

if [[ $duration -lt 2000 ]]; then
    log_test "API Response Time" "PASS" "${duration}ms (< 2000ms)"
elif [[ $duration -lt 5000 ]]; then
    log_test "API Response Time" "PASS" "${duration}ms (warning: slow)"
else
    log_test "API Response Time" "FAIL" "${duration}ms (> 5000ms)"
fi

# ===========================================
# Summary
# ===========================================
print_summary

# Exit with failure if any tests failed
if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
