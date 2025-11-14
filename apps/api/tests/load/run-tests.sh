#!/bin/bash
#
# Run K6 Load Tests for Plinto Authentication
#
# Usage:
#   ./tests/load/run-tests.sh [smoke|load|stress|spike]
#
# Test Types:
#   smoke  - Minimal load to verify functionality
#   load   - Normal load test (100 concurrent users)
#   stress - High load stress test (500 concurrent users)
#   spike  - Sudden spike test

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
TEST_TYPE="${1:-load}"

echo -e "${GREEN}=== Plinto Load Testing ===${NC}"
echo -e "Base URL: ${YELLOW}${BASE_URL}${NC}"
echo -e "Test Type: ${YELLOW}${TEST_TYPE}${NC}\n"

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo -e "${RED}Error: k6 is not installed${NC}"
    echo "Install k6 from: https://k6.io/docs/getting-started/installation/"
    exit 1
fi

# Check if API is running
echo "Checking if API is available..."
if ! curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo -e "${RED}Error: API is not responding at ${BASE_URL}${NC}"
    echo "Please start the API server first"
    exit 1
fi
echo -e "${GREEN}✓ API is available${NC}\n"

# Create results directory
mkdir -p tests/load/results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="tests/load/results/${TEST_TYPE}_${TIMESTAMP}"
mkdir -p "${RESULTS_DIR}"

# Run test based on type
case ${TEST_TYPE} in
  smoke)
    echo -e "${YELLOW}Running Smoke Test (minimal load)...${NC}"
    k6 run \
      --vus 1 \
      --duration 30s \
      --out json="${RESULTS_DIR}/results.json" \
      -e BASE_URL="${BASE_URL}" \
      tests/load/auth_flows.js
    ;;

  load)
    echo -e "${YELLOW}Running Load Test (100 concurrent users)...${NC}"
    k6 run \
      --vus 100 \
      --duration 2m \
      --out json="${RESULTS_DIR}/results.json" \
      -e BASE_URL="${BASE_URL}" \
      tests/load/auth_flows.js
    ;;

  stress)
    echo -e "${YELLOW}Running Stress Test (500 concurrent users)...${NC}"
    k6 run \
      --vus 500 \
      --duration 3m \
      --out json="${RESULTS_DIR}/results.json" \
      -e BASE_URL="${BASE_URL}" \
      tests/load/auth_flows.js
    ;;

  spike)
    echo -e "${YELLOW}Running Spike Test (sudden traffic spike)...${NC}"
    k6 run \
      --stage 10s:10 \
      --stage 5s:500 \
      --stage 10s:500 \
      --stage 5s:10 \
      --stage 10s:10 \
      --out json="${RESULTS_DIR}/results.json" \
      -e BASE_URL="${BASE_URL}" \
      tests/load/auth_flows.js
    ;;

  *)
    echo -e "${RED}Unknown test type: ${TEST_TYPE}${NC}"
    echo "Valid types: smoke, load, stress, spike"
    exit 1
    ;;
esac

# Save summary
if [ -f "load_test_results.json" ]; then
  mv load_test_results.json "${RESULTS_DIR}/summary.json"
  echo -e "\n${GREEN}✓ Test completed successfully${NC}"
  echo -e "Results saved to: ${YELLOW}${RESULTS_DIR}${NC}"
else
  echo -e "\n${YELLOW}⚠ Test completed (no summary file)${NC}"
fi

# Check thresholds
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ All thresholds passed${NC}"
else
  echo -e "${RED}✗ Some thresholds failed${NC}"
  exit 1
fi
