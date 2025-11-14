#!/bin/bash
#
# Plinto Local Demo - Start All Services
#
# Launches complete local demonstration:
# - API server with performance monitoring
# - Landing site
# - Demo application
# - Redis (for caching)
#
# Usage: ./scripts/start-local-demo.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║              PLINTO LOCAL DEMO ENVIRONMENT                 ║"
echo "║                                                            ║"
echo "║  Complete authentication platform demonstration            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 installed${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js installed${NC}"

# Check Redis
if ! command -v redis-server &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis not found - caching will be disabled${NC}"
    REDIS_AVAILABLE=false
else
    echo -e "${GREEN}✓ Redis installed${NC}"
    REDIS_AVAILABLE=true
fi

echo ""

# Set up environment
export ENVIRONMENT=development
export DATABASE_URL="sqlite+aiosqlite:///./plinto_demo.db"
export REDIS_URL="redis://localhost:6379/0"
export DEBUG=true

# Create logs directory
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"

    # Kill all background processes
    jobs -p | xargs -r kill 2>/dev/null || true

    # Wait for processes to terminate
    sleep 2

    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Redis if available
if [ "$REDIS_AVAILABLE" = true ]; then
    echo -e "${BLUE}Starting Redis...${NC}"
    redis-server --daemonize yes --port 6379 > logs/redis.log 2>&1
    sleep 2

    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis running on port 6379${NC}"
    else
        echo -e "${YELLOW}⚠ Redis failed to start - continuing without cache${NC}"
    fi
    echo ""
fi

# Start API Server
echo -e "${BLUE}Starting API Server...${NC}"
cd apps/api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../../logs/api.log 2>&1 &
API_PID=$!
cd ../..

# Wait for API to be ready
echo -e "${YELLOW}Waiting for API server to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API server running on http://localhost:8000${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ API server failed to start${NC}"
        cat logs/api.log
        exit 1
    fi
done
echo ""

# Start Landing Site
echo -e "${BLUE}Starting Landing Site...${NC}"
cd apps/landing
npm install --silent > /dev/null 2>&1
npm run dev > ../../logs/landing.log 2>&1 &
LANDING_PID=$!
cd ../..

# Wait for landing site to be ready
echo -e "${YELLOW}Waiting for landing site to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Landing site running on http://localhost:3000${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠ Landing site taking longer than expected${NC}"
        break
    fi
done
echo ""

# Display service status
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    SERVICES RUNNING                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📡 API Server:${NC}        http://localhost:8000"
echo -e "   ${YELLOW}→ API Docs:${NC}        http://localhost:8000/docs"
echo -e "   ${YELLOW}→ Health Check:${NC}    http://localhost:8000/health"
echo -e "   ${YELLOW}→ Metrics:${NC}         http://localhost:8000/metrics"
echo ""
echo -e "${BLUE}🌐 Landing Site:${NC}     http://localhost:3000"
echo -e "   ${YELLOW}→ Features:${NC}        http://localhost:3000/features"
echo -e "   ${YELLOW}→ Pricing:${NC}         http://localhost:3000/pricing"
echo -e "   ${YELLOW}→ Docs:${NC}            http://localhost:3000/docs"
echo ""
if [ "$REDIS_AVAILABLE" = true ]; then
    echo -e "${BLUE}💾 Redis Cache:${NC}      localhost:6379"
    echo ""
fi

# Display demo walkthrough
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    DEMO WALKTHROUGH                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}1. Landing Site Tour${NC}"
echo -e "   ${YELLOW}→${NC} Visit http://localhost:3000"
echo -e "   ${YELLOW}→${NC} Explore features, pricing, documentation"
echo -e "   ${YELLOW}→${NC} Check quickstart guide"
echo ""
echo -e "${BLUE}2. API Documentation${NC}"
echo -e "   ${YELLOW}→${NC} Visit http://localhost:8000/docs"
echo -e "   ${YELLOW}→${NC} Try the interactive API explorer"
echo -e "   ${YELLOW}→${NC} Test signup, login, MFA endpoints"
echo ""
echo -e "${BLUE}3. Performance Metrics${NC}"
echo -e "   ${YELLOW}→${NC} Visit http://localhost:8000/metrics"
echo -e "   ${YELLOW}→${NC} Check response time headers (X-Response-Time)"
echo -e "   ${YELLOW}→${NC} Monitor cache hit rates"
echo ""
echo -e "${BLUE}4. Run Journey Tests${NC}"
echo -e "   ${YELLOW}→${NC} Open new terminal"
echo -e "   ${YELLOW}→${NC} Run: ./scripts/run-demo-tests.sh"
echo -e "   ${YELLOW}→${NC} See all features working end-to-end"
echo ""

# Display logs location
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                         LOGS                               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "API logs:     ${YELLOW}tail -f logs/api.log${NC}"
echo -e "Landing logs: ${YELLOW}tail -f logs/landing.log${NC}"
if [ "$REDIS_AVAILABLE" = true ]; then
    echo -e "Redis logs:   ${YELLOW}tail -f logs/redis.log${NC}"
fi
echo ""

# Keep script running
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  DEMO ENVIRONMENT READY                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for interrupt
wait
