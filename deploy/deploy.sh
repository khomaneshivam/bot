#!/usr/bin/env bash
# ==============================================================================
# QuantAI Trading Bot - Production Deployment Script
# Pulls latest code, rebuilds containers, and performs health verification
# ==============================================================================
set -e

REPO_DIR="${1:-$HOME/bot}"

echo "🔄 Deploying QuantAI Trading Bot in: $REPO_DIR"

if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
else
    echo "❌ Directory $REPO_DIR does not exist! Please clone the repository first."
    exit 1
fi

# Ensure git pulls latest changes
echo "📥 Fetching latest code from origin/main..."
git fetch origin main
git reset --hard origin/main

# Verify that .env exists
if [ ! -f "forex-trading-bot/.env" ]; then
    if [ -f ".env" ]; then
        cp .env forex-trading-bot/.env
    elif [ -f "forex-trading-bot/.env.production.template" ]; then
        echo "⚠️ forex-trading-bot/.env not found! Copying from template. Please update with your real secrets!"
        cp forex-trading-bot/.env.production.template forex-trading-bot/.env
    fi
fi

# Ensure persistent data directory exists
mkdir -p forex-trading-bot/data

# Restart and rebuild containers
echo "🐳 Rebuilding and restarting Docker containers via docker-compose.prod.yml..."
COMPOSE_FILE="docker-compose.prod.yml"

if docker compose version &> /dev/null; then
    docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
    docker compose -f "$COMPOSE_FILE" up -d --build
else
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    docker-compose -f "$COMPOSE_FILE" up -d --build
fi

# Wait for container startup and health check
echo "⏳ Waiting for health check verification via Nginx reverse proxy..."
sleep 15

MAX_RETRIES=10
COUNT=0
HEALTHY=0

while [ $COUNT -lt $MAX_RETRIES ]; do
    # Check through Nginx proxy (port 80)
    if curl -s -f http://localhost/metrics > /dev/null 2>&1 || curl -s -f http://localhost:8000/metrics > /dev/null 2>&1; then
        echo "✅ QuantAI Terminal is live and healthy (reverse-proxy verified)!"
        HEALTHY=1
        break
    else
        echo "⏳ Service starting up... ($((COUNT+1))/$MAX_RETRIES)"
        sleep 5
        COUNT=$((COUNT+1))
    fi
done

if [ $HEALTHY -eq 0 ]; then
    echo "⚠️ Warning: Healthcheck did not respond within timeout."
    echo "Checking docker logs:"
    docker compose -f "$COMPOSE_FILE" logs --tail=50
    exit 1
fi

echo "🚀 Deployment completed successfully!"
