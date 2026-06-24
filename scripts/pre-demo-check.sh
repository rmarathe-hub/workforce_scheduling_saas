#!/usr/bin/env bash
# Quick health checks before a live portfolio demo.
set -euo pipefail

API_URL="${E2E_API_BASE_URL:-https://workforce-scheduling-api.onrender.com}"
FRONTEND_URL="${E2E_BASE_URL:-https://workforce-scheduling-saas.vercel.app}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> API health (${API_URL})"
health_json="$(curl -sf "${API_URL}/health")"
echo "${health_json}" | python3 -m json.tool

readiness_code="$(curl -s -o /dev/null -w '%{http_code}' "${API_URL}/readiness")"
echo "readiness HTTP ${readiness_code}"
if [[ "${readiness_code}" != "200" ]]; then
  echo "FAIL: readiness not 200"
  exit 1
fi

echo ""
echo "==> Frontend (${FRONTEND_URL})"
frontend_code="$(curl -s -o /dev/null -w '%{http_code}' "${FRONTEND_URL}")"
echo "HTTP ${frontend_code}"
if [[ "${frontend_code}" != "200" ]]; then
  echo "FAIL: frontend not 200"
  exit 1
fi

echo ""
echo "==> Local notification worker"
if pgrep -fl notification_worker >/dev/null 2>&1; then
  echo "WARN: notification_worker is running — stop it before demoing Lambda on prod"
  pgrep -fl notification_worker
  exit 1
fi
echo "OK — no local worker"

echo ""
echo "==> SQS queue (optional)"
if [[ -f "${ROOT}/backend/.env" ]]; then
  cd "${ROOT}/backend"
  if python scripts/validate_notification_queues.py; then
    :
  else
    echo "WARN: queue validation failed or DLQ not readable — check AWS Console"
  fi
else
  echo "SKIP — no backend/.env"
fi

echo ""
echo "==> Pre-demo check passed"
echo "Demo script: docs/DEMO.md"
