#!/bin/bash

# Simple Plinto Production Status Check
# Quick validation script for alpha launch readiness

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════"
echo "     Plinto Alpha Launch Readiness Check - $(date)"
echo "════════════════════════════════════════════════════════"
echo ""

# Initialize counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to check a service
check_service() {
    local name=$1
    local url=$2
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "🔍 Checking $name... "
    
    if response=$(curl -s -w "%{http_code}" --max-time 10 "$url" 2>/dev/null); then
        http_code=${response: -3}
        
        if [[ "$http_code" =~ ^(200|301|302|308)$ ]]; then
            echo -e "${GREEN}✅ UP (HTTP $http_code)${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            echo -e "${YELLOW}⚠️ WARNING (HTTP $http_code)${NC}"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
    else
        echo -e "${RED}❌ DOWN (Timeout)${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check SSL certificate
check_ssl() {
    local domain=$1
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "🔒 SSL for $domain... "
    
    if echo | openssl s_client -connect $domain:443 -servername $domain 2>/dev/null | openssl x509 -noout -checkend 604800 &>/dev/null; then
        echo -e "${GREEN}✅ Valid${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠️ Expiring Soon${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

echo "━━━ Core Service Health Checks ━━━"
echo ""

# Check all core services
check_service "API Health" "https://api.plinto.dev/health"
check_service "API Auth" "https://api.plinto.dev/api/v1/auth/status"
check_service "Marketing Site" "https://www.plinto.dev"
check_service "Main App" "https://app.plinto.dev"
check_service "Documentation" "https://docs.plinto.dev"
check_service "Admin Panel" "https://admin.plinto.dev"
check_service "Demo App" "https://demo.plinto.dev"

echo ""
echo "━━━ SSL Certificate Checks ━━━"
echo ""

# Check SSL certificates
check_ssl "api.plinto.dev"
check_ssl "www.plinto.dev"
check_ssl "app.plinto.dev"
check_ssl "docs.plinto.dev"
check_ssl "admin.plinto.dev"
check_ssl "demo.plinto.dev"

echo ""
echo "━━━ API Functionality Checks ━━━"
echo ""

# Test API endpoints
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "🔧 API OpenAPI docs... "
if curl -s "https://api.plinto.dev/openapi.json" | grep -q "Plinto API"; then
    echo -e "${GREEN}✅ Available${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ Not Available${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "🔧 Database connectivity... "
if curl -s "https://api.plinto.dev/ready" | grep -q '"database":true'; then
    echo -e "${GREEN}✅ Connected${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ Not Connected${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo -n "🔧 Redis connectivity... "
if curl -s "https://api.plinto.dev/ready" | grep -q '"redis":true'; then
    echo -e "${GREEN}✅ Connected${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ Not Connected${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "                    FINAL RESULTS                        "
echo "════════════════════════════════════════════════════════"
echo ""

# Calculate statistics
PASS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo "📊 Checks Summary:"
echo "   Total Checks: $TOTAL_CHECKS"
echo -e "   Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "   Failed: ${RED}$FAILED_CHECKS${NC}"
echo "   Pass Rate: $PASS_RATE%"
echo ""

# Determine overall status
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}🎉 STATUS: ALPHA LAUNCH READY${NC}"
    echo -e "${GREEN}All systems operational - ready for alpha users!${NC}"
    EXIT_CODE=0
elif [ $PASS_RATE -ge 85 ]; then
    echo -e "${YELLOW}🔄 STATUS: ALPHA LAUNCH READY (with minor issues)${NC}"
    echo -e "${YELLOW}Core systems operational - alpha launch possible with monitoring${NC}"
    EXIT_CODE=0
elif [ $PASS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠️ STATUS: CONDITIONAL ALPHA READY${NC}"
    echo -e "${YELLOW}Address critical issues before full alpha launch${NC}"
    EXIT_CODE=1
else
    echo -e "${RED}❌ STATUS: NOT READY FOR ALPHA${NC}"
    echo -e "${RED}Critical failures - postpone alpha launch${NC}"
    EXIT_CODE=2
fi

echo ""
echo "Next recommended action: Set up monitoring accounts (UptimeRobot, Sentry)"
echo "Created: $(date)"
echo "════════════════════════════════════════════════════════"

exit $EXIT_CODE