#!/usr/bin/env bash
set -euo pipefail

echo "[redeploy] Building fresh images…"
docker compose build --pull --no-cache

echo "[redeploy] Stopping current containers…"
docker compose down

echo "[redeploy] Starting containers…"
docker compose up -d

echo "[redeploy] Status:"
docker compose ps

echo "[redeploy] Health check:"
curl -fsS http://localhost:18080/health || true

