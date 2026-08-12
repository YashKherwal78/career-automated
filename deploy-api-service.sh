#!/bin/bash
# Deploy a dedicated FastAPI service as a separate Docker Swarm service.
# Reads all secrets from the project .env file — never hardcode credentials here.
#
# Usage:
#   bash deploy-api-service.sh
#   bash deploy-api-service.sh --env /path/to/custom.env

set -e

# ── Config ────────────────────────────────────────────────────────────────────
SERVICE_NAME="careerautomated-api"
IMAGE="careerautomated-api:latest"
NETWORK="dokploy-network"
ENV_FILE="${1:-$(dirname "$0")/.env}"

# ── Validate env file ─────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ ERROR: .env file not found at: $ENV_FILE"
  echo "   Pass path as first argument: bash deploy-api-service.sh /path/to/.env"
  exit 1
fi

echo "=== Deploying dedicated FastAPI service ==="
echo "Image:    $IMAGE"
echo "Service:  $SERVICE_NAME"
echo "Env file: $ENV_FILE"
echo ""

# ── Load env vars from .env ───────────────────────────────────────────────────
# Build --env flags for docker service create by reading .env
ENV_ARGS=()
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip comments and blank lines
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
  # Skip lines without = sign
  [[ "$line" != *"="* ]] && continue
  ENV_ARGS+=(--env "$line")
done < "$ENV_FILE"

echo "[1/3] Loaded ${#ENV_ARGS[@]} environment variables from .env"

# ── Remove existing service if it exists (idempotent) ─────────────────────────
if sudo docker service ls --format '{{.Name}}' | grep -q "^${SERVICE_NAME}$"; then
  echo "[2/3] Removing existing $SERVICE_NAME service..."
  sudo docker service rm "$SERVICE_NAME"
  sleep 3
else
  echo "[2/3] No existing $SERVICE_NAME service — fresh deploy."
fi

# ── Create the service ────────────────────────────────────────────────────────
echo "[3/3] Creating $SERVICE_NAME service..."

sudo docker service create \
  --name "$SERVICE_NAME" \
  --replicas 1 \
  --network "$NETWORK" \
  --restart-condition on-failure \
  --restart-delay 10s \
  --mount type=bind,source="$(cd "$(dirname "$0")" && pwd)/backend/data",target=/app/data \
  --label "traefik.enable=true" \
  --label "traefik.http.routers.${SERVICE_NAME}.rule=Host(\`api.careerautomated.in\`)" \
  --label "traefik.http.routers.${SERVICE_NAME}.entrypoints=websecure" \
  --label "traefik.http.routers.${SERVICE_NAME}.tls.certresolver=letsencrypt" \
  --label "traefik.http.routers.${SERVICE_NAME}-http.rule=Host(\`api.careerautomated.in\`)" \
  --label "traefik.http.routers.${SERVICE_NAME}-http.entrypoints=web" \
  --label "traefik.http.routers.${SERVICE_NAME}-http.middlewares=redirect-to-https@file" \
  --label "traefik.http.services.${SERVICE_NAME}.loadbalancer.server.port=8000" \
  \
  "${ENV_ARGS[@]}" \
  --workdir /app \
  "$IMAGE" \
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level info

echo ""
echo "=== Waiting 15s for service to stabilise... ==="
sleep 15

echo ""
echo "=== Service status ==="
sudo docker service ls | grep -E "NAME|careerautomated"

echo ""
echo "=== Task health ==="
sudo docker service ps "$SERVICE_NAME" --no-trunc 2>/dev/null | head -5

echo ""
echo "=== API health check ==="
sleep 3
HTTP_STATUS=$(curl -sk -o /dev/null -w "%{http_code}" https://api.careerautomated.in/api/v1/health)
if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ https://api.careerautomated.in/api/v1/health → $HTTP_STATUS"
else
  echo "❌ https://api.careerautomated.in/api/v1/health → $HTTP_STATUS (may still be starting)"
fi
