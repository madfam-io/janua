#!/bin/bash
# Wait for all test environment services to be healthy before running tests

set -e

echo "🔄 Waiting for test services to be ready..."

# Colors for output
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Maximum wait time (3 minutes)
MAX_WAIT=180
ELAPSED=0
INTERVAL=2

# Function to check if a service is responding
check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        return 0
    else
        return 1
    fi
}

# Function to wait for a service
wait_for_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    printf "  Waiting for ${YELLOW}$name${NC}... "

    local service_wait=0
    while [ $service_wait -lt $MAX_WAIT ]; do
        if check_service "$name" "$url" "$expected_code"; then
            echo -e "${GREEN}✓${NC}"
            return 0
        fi
        sleep $INTERVAL
        service_wait=$((service_wait + INTERVAL))
    done

    echo -e "\n❌ $name failed to start within ${MAX_WAIT}s"
    return 1
}

# Wait for each service
wait_for_service "PostgreSQL" "http://localhost:5432" "000" || exit 1
wait_for_service "Redis" "http://localhost:6379" "000" || exit 1
wait_for_service "API (health)" "http://localhost:8000/health" "200" || exit 1
wait_for_service "API (ready)" "http://localhost:8000/ready" "200" || exit 1
wait_for_service "Landing Page" "http://localhost:3000" "200" || exit 1
wait_for_service "Test App" "http://localhost:3001" "200" || exit 1
wait_for_service "Dashboard" "http://localhost:3002" "200" || exit 1

echo -e "\n${GREEN}✅ All services are ready!${NC}"
echo ""
