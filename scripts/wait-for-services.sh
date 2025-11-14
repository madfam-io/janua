#!/bin/bash
# Wait for Docker Compose services to be healthy before running tests

set -e

echo "⏳ Waiting for services to become healthy..."

MAX_ATTEMPTS=60
SLEEP_INTERVAL=2

# Wait for PostgreSQL
wait_for_postgres() {
  echo "Waiting for PostgreSQL..."
  for i in $(seq 1 $MAX_ATTEMPTS); do
    if docker exec plinto-postgres-test pg_isready -U test_user -d plinto_test > /dev/null 2>&1; then
      echo "✅ PostgreSQL is ready"
      return 0
    fi
    echo "   Attempt $i/$MAX_ATTEMPTS..."
    sleep $SLEEP_INTERVAL
  done
  echo "❌ PostgreSQL failed to become ready"
  return 1
}

# Wait for Redis
wait_for_redis() {
  echo "Waiting for Redis..."
  for i in $(seq 1 $MAX_ATTEMPTS); do
    if docker exec plinto-redis-test redis-cli ping > /dev/null 2>&1; then
      echo "✅ Redis is ready"
      return 0
    fi
    echo "   Attempt $i/$MAX_ATTEMPTS..."
    sleep $SLEEP_INTERVAL
  done
  echo "❌ Redis failed to become ready"
  return 1
}

# Wait for API
wait_for_api() {
  echo "Waiting for API..."
  for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
      echo "✅ API is ready"
      return 0
    fi
    echo "   Attempt $i/$MAX_ATTEMPTS..."
    sleep $SLEEP_INTERVAL
  done
  echo "❌ API failed to become ready"
  return 1
}

# Wait for Landing Page
wait_for_landing() {
  echo "Waiting for Landing Page..."
  for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
      echo "✅ Landing Page is ready"
      return 0
    fi
    echo "   Attempt $i/$MAX_ATTEMPTS..."
    sleep $SLEEP_INTERVAL
  done
  echo "❌ Landing Page failed to become ready"
  return 1
}

# Wait for Test App
wait_for_test_app() {
  echo "Waiting for Test App..."
  for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -f http://localhost:3001 > /dev/null 2>&1; then
      echo "✅ Test App is ready"
      return 0
    fi
    echo "   Attempt $i/$MAX_ATTEMPTS..."
    sleep $SLEEP_INTERVAL
  done
  echo "⚠️  Test App not ready (non-critical)"
  return 0  # Non-blocking for now
}

# Run all health checks
wait_for_postgres
wait_for_redis
wait_for_api
wait_for_landing
wait_for_test_app

echo ""
echo "✅ All services are ready!"
echo "🚀 You can now run journey tests"
echo ""
