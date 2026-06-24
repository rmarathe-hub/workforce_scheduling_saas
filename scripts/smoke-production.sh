#!/usr/bin/env bash
# Run deployed API + frontend production smoke tests (Day 33).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export E2E_API_BASE_URL="${E2E_API_BASE_URL:-https://workforce-scheduling-api.onrender.com}"
export E2E_BASE_URL="${E2E_BASE_URL:-https://workforce-scheduling-saas.vercel.app}"
export E2E_FRONTEND_URL="${E2E_FRONTEND_URL:-$E2E_BASE_URL}"
export E2E_SMOKE=1
export E2E_SKIP_WEBSERVER=1

echo "==> API smoke (${E2E_API_BASE_URL})"
cd "$ROOT/backend"
if [[ -x .venv/bin/pytest ]]; then
  .venv/bin/pytest -m e2e -q
else
  pytest -m e2e -q
fi

echo "==> Frontend smoke (${E2E_BASE_URL})"
cd "$ROOT/frontend"
npm run test:e2e:prod

echo "==> Production smoke passed"
