#!/bin/bash

# Plinto Development Setup Script
# This script sets up local development environment with subdomain routing

echo "🚀 Setting up Plinto development environment..."

# Add local domains to /etc/hosts
echo "
# Plinto local development
127.0.0.1 plinto.local
127.0.0.1 app.plinto.local
127.0.0.1 admin.plinto.local
127.0.0.1 api.plinto.local
" | sudo tee -a /etc/hosts

# Install dependencies for all apps
echo "📦 Installing dependencies..."
cd marketing && yarn install && cd ..
cd dashboard && yarn install && cd ..
cd admin && yarn install && cd ..
cd api && pip install -r requirements.txt && cd ..

# Start all services
echo "🔧 Starting all services..."

# Start API with Docker Compose
cd api
docker-compose up -d
cd ..

# Start frontend apps
cd marketing && yarn dev &
MARKETING_PID=$!
cd ..

cd dashboard && yarn dev &
DASHBOARD_PID=$!
cd ..

cd admin && yarn dev &
ADMIN_PID=$!
cd ..

echo "✅ Development environment is ready!"
echo ""
echo "🌐 Access your apps at:"
echo "   Marketing: http://plinto.local"
echo "   Dashboard: http://app.plinto.local"
echo "   Admin: http://admin.plinto.local"
echo "   API: http://api.plinto.local"
echo ""
echo "📝 Don't forget to start nginx with: nginx -c $(pwd)/nginx.conf"
echo ""
echo "Process IDs:"
echo "   Marketing: $MARKETING_PID"
echo "   Dashboard: $DASHBOARD_PID"
echo "   Admin: $ADMIN_PID"
echo ""
echo "To stop all services, run: killall node && docker-compose -f api/docker-compose.yml down"