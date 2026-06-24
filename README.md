# Workforce Scheduling SaaS (ShiftOps)

Multi-tenant workforce scheduling SaaS — FastAPI backend, React frontend, Supabase Postgres, and AWS (S3, SQS, Lambda).

## Architecture

### Deployed stack

| Layer | Service | URL / resource |
|-------|---------|----------------|
| Frontend | Vercel | https://workforce-scheduling-saas.vercel.app |
| API | Render | https://workforce-scheduling-api.onrender.com |
| Database | Supabase Postgres | Connection via `DATABASE_URL` |
| Documents | S3 | `shiftops-documents-*` bucket |
| Notification jobs | SQS | `shiftops-notifications-queue` |
| Notification consumer | AWS Lambda | `shiftops-notification-consumer` (Python 3.12) |

```mermaid
flowchart LR
  subgraph client [Client]
    Browser[React SPA on Vercel]
  end
  subgraph api [API tier]
    Render[FastAPI on Render]
  end
  subgraph data [Data and async]
    DB[(Supabase Postgres)]
    S3[(S3 documents)]
    SQS[SQS notification queue]
    Lambda[Lambda consumer]
    DLQ[Dead-letter queue]
  end
  Browser -->|HTTPS JWT| Render
  Render --> DB
  Render --> S3
  Render -->|enqueue SEND_NOTIFICATION| SQS
  SQS --> Lambda
  Lambda --> DB
  SQS -.->|max retries| DLQ
```

**Request path:** browser → Vercel SPA → Render API → Supabase (reads/writes).

**Async notification path:** API creates `PENDING` row → SQS message → Lambda marks `SENT` → bell and `/notifications` show the item.

**Document path:** API issues presigned S3 URLs; uploads go browser → S3 directly.

The API stays on Render. Lambda is **only** the SQS consumer — not a replacement for the HTTP API.

## Portfolio

| Resource | Description |
|----------|-------------|
| [Live demo](https://workforce-scheduling-saas.vercel.app) | Production frontend |
| [docs/DEMO.md](docs/DEMO.md) | 3-minute demo script, resume bullets, screenshot checklist |
| [docs/COMPLETION.md](docs/COMPLETION.md) | Final sign-off checklist and Week 6 wrap |
| `./scripts/pre-demo-check.sh` | Health + worker + queue check before interviews |

**Highlight features:** multi-tenant RBAC, schedule generation + conflict detection, publish workflow, time-off and shift swaps, S3 employee documents, async notifications (SQS → Lambda), CI + production smoke tests.

### Repository layout

```
workforce_scheduling_saas/
  backend/
    app/
      main.py                 # FastAPI app, middleware, routes
      routes/                 # auth, orgs, scheduling, notifications, …
      services/
        notification_processor.py   # shared SQS delivery logic
        queue.py                    # SQS enqueue
      lambda_handlers/
        sqs_notification_handler.py # AWS Lambda entry point
    scripts/                  # worker, Lambda build, queue validation
    tests/
  frontend/                   # React + Vite + Playwright
  scripts/smoke-production.sh # deployed API + frontend smoke
  .github/workflows/          # CI
```

## Backend

### Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL and secrets
alembic upgrade head
uvicorn app.main:app --reload
```

### Verify

- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/readiness
- API docs: http://localhost:8000/docs
- Tests: `pytest`

### Auth endpoints (Day 2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account + org (`email`, `password`, `full_name`, `organization_name`) |
| POST | `/auth/login` | Returns JWT `access_token` |
| GET | `/auth/me` | Current user (requires `Authorization: Bearer <token>`) |

### Organization endpoints (Day 3)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/organizations/me` | List orgs + roles for current user |
| POST | `/organizations` | Create org (caller becomes OWNER) |
| GET | `/organizations/{id}` | Get org (members only) |

Roles: `OWNER` > `MANAGER` > `EMPLOYEE` (see `app/auth/permissions.py`)

### Organization resources (Day 4)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/organizations/{id}/locations` | Create location (manager+) |
| GET | `/organizations/{id}/locations` | List locations |
| POST | `/organizations/{id}/job-roles` | Create job role e.g. Cashier (manager+) |
| GET | `/organizations/{id}/job-roles` | List job roles |
| POST | `/organizations/{id}/members` | Add manager/employee (manager+) |
| GET | `/organizations/{id}/employees` | List employees with job roles |

### Scheduling (Day 5)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/organizations/{id}/coverage-requirements` | Create staffing need (manager+) |
| GET | `/organizations/{id}/schedules/{week_start}` | Week view: requirements + shifts |
| POST | `/organizations/{id}/shifts` | Create shift (manager+) |
| PATCH | `/organizations/{id}/shifts/{shift_id}/assign` | Assign employee (manager+) |
| GET | `/organizations/{id}/my-shifts?week_start=` | Employee's assigned shifts |

### Structure

See [Repository layout](#repository-layout) above. Core domains: `routes/` (HTTP), `services/` (business logic), `models/` + Alembic migrations, `lambda_handlers/` (SQS consumer).

## Frontend (Day 6)

### Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173

### Pages

| Route | Role | Purpose |
|-------|------|---------|
| `/login` | all | Sign in |
| `/register` | all | Create account + organization |
| `/manager/schedule` | owner/manager | Weekly schedule, assign shifts |
| `/manager/coverage/new` | owner/manager | Create coverage requirement |
| `/employee/shifts` | employee | View assigned shifts |

### Local demo flow

1. Start backend (`uvicorn`) and frontend (`npm run dev`)
2. Register as owner → quick setup: location + job role + employee
3. Create coverage → add shift → assign employee
4. Log in as employee → see shift on **My shifts**

## Testing

### Backend (pytest)

Integration tests use FastAPI `TestClient` against your database. Prefer a dedicated test database:

```bash
cd backend
source .venv/bin/activate
export TEST_DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/postgres_test"
pytest -m "not future"
```

If `TEST_DATABASE_URL` is unset, tests fall back to `DATABASE_URL` from `.env`.

| Command | Purpose |
|---------|---------|
| `pytest -m "not future"` | All local backend tests (recommended) |
| `pytest -m "not e2e and not future"` | Skip deployed API smoke tests |
| `pytest -m e2e` | Deployed API smoke tests (requires `E2E_API_BASE_URL`) |

**Backend coverage includes:** auth/session, RBAC, multi-tenant isolation, org resources, availability, time-off, scheduling CRUD, schedule generation, conflict detection, publish workflow, SQS notifications, Lambda handler + delivery pipeline, consumer safety guards, health/readiness, and integration flows.

**Notification / Lambda test subset** (fast, no deployed AWS):

```bash
cd backend
pytest tests/test_notification_queue.py \
  tests/test_notification_reliability.py \
  tests/test_notification_delivery_pipeline.py \
  tests/test_lambda_notification_handler.py \
  tests/test_consumer_safety.py -q
```

**Deployed API smoke tests:**

```bash
cd backend
export E2E_API_BASE_URL="https://workforce-scheduling-api.onrender.com"
pytest -m e2e
```

| Variable | Used by | Description |
|----------|---------|-------------|
| `TEST_DATABASE_URL` | pytest | Optional separate DB for local tests |
| `E2E_API_BASE_URL` | pytest `-m e2e` | Deployed Render API base URL |

### Frontend build

```bash
cd frontend
npm run build
```

### Playwright E2E (local)

Auto-starts backend + Vite when not already running. Uses `http://localhost:5173` (not `127.0.0.1`) for CORS compatibility.

```bash
cd frontend
npm install
npx playwright install chromium
npm run test:e2e
```

| Script | Purpose |
|--------|---------|
| `npm run test:e2e` | Full local Playwright suite |
| `npm run test:e2e:headed` | Run with visible browser |
| `npm run test:e2e:ui` | Playwright UI mode |
| `npm run test:e2e:smoke` | Production smoke subset only (alias of `test:e2e:prod`) |
| `npm run test:e2e:prod` | Production smoke against deployed Vercel frontend |
| `npm run test:all` | `build` + full E2E |

**Playwright coverage includes:** auth (positive/negative), protected routes, owner setup, coverage, generate, publish, conflicts, employee flows, RBAC (both directions), manager time-off/availability, navigation, employee-published-shift handoff, and production smoke (notifications + documents pages).

### Playwright production smoke

Runs against deployed Vercel + Render without starting local servers. Creates orgs named `Smoke Test Org YYYYMMDD-HHMMSS` so production data is easy to spot.

**Frontend only:**

```bash
cd frontend
export E2E_SMOKE=1
export E2E_SKIP_WEBSERVER=1
export E2E_BASE_URL="https://workforce-scheduling-saas.vercel.app"
npm run test:e2e:prod
```

**API + frontend (full production smoke):**

```bash
chmod +x scripts/smoke-production.sh   # once
./scripts/smoke-production.sh
```

Or run separately:

```bash
# API smoke
cd backend
export E2E_API_BASE_URL="https://workforce-scheduling-api.onrender.com"
pytest -m e2e

# Frontend smoke
cd frontend
export E2E_SMOKE=1 E2E_SKIP_WEBSERVER=1
export E2E_BASE_URL="https://workforce-scheduling-saas.vercel.app"
npm run test:e2e:prod
```

| Variable | Description |
|----------|-------------|
| `E2E_BASE_URL` / `E2E_FRONTEND_URL` | Deployed frontend URL |
| `E2E_API_BASE_URL` | Deployed API URL (backend `pytest -m e2e`) |
| `E2E_SMOKE=1` | Run production smoke project only |
| `E2E_SKIP_WEBSERVER=1` | Do not auto-start backend/Vite |

**Smoke coverage:** login page, register → manager dashboard, generate + validate schedule, publish + activity log, notifications page (manager + employee), documents pages (manager employee-documents + employee documents).

### Pre-push checklist

1. `cd backend && pytest -m "not future"`
2. `cd frontend && npm run build`
3. `cd frontend && npm run test:e2e`
4. Optional deployed: `./scripts/smoke-production.sh` or `pytest -m e2e` + `npm run test:e2e:prod`

### GitHub Actions CI

Runs automatically on push/PR to `main`:

| Workflow | What it runs |
|----------|----------------|
| `backend-tests.yml` | `alembic upgrade head` + `pytest -m "not e2e and not future"` |
| `frontend-tests.yml` | `npm ci` + `npm run build` |
| `playwright-e2e.yml` | Manual only (`workflow_dispatch`) |

**Required GitHub secret** (repo → Settings → Secrets and variables → Actions):

| Secret | Purpose |
|--------|---------|
| `TEST_DATABASE_URL` | Supabase Postgres URL for CI test database |

Optional: set `JWT_SECRET_KEY` secret if you prefer not to use the inline CI default in the workflow.

Playwright in CI needs the same `TEST_DATABASE_URL` secret because the suite auto-starts the backend against that database.

Important UI elements use `data-testid` attributes for stable selectors.

## Observability

### Health and readiness

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness + config summary (always `200`) |
| `GET /readiness` | Traffic readiness (`200` when DB is up, `503` when not) |

Example `/health` response:

```json
{
  "status": "ok",
  "database": "ok",
  "s3_configured": true,
  "sqs_configured": true,
  "environment": "production"
}
```

- `status` is `degraded` when the database check fails (endpoint still returns `200` for Render liveness).
- No secrets, AWS keys, or database URLs are exposed.
- Responses include `X-Request-ID` (echoes client header or generates a UUID).

Set `ENVIRONMENT=production` on Render for accurate `environment` in health checks.

### Structured logging

Important actions log at `INFO`:

- Schedule publish (`publish_service`)
- S3 document upload complete (`document_service`)
- SQS notification enqueue (`queue`)

## Async notifications (SQS)

ShiftOps records in-app notifications in Postgres and optionally delivers them through AWS SQS.

### Flow

1. API action creates a notification row as `PENDING` (when SQS is configured).
2. API enqueues a `SEND_NOTIFICATION` job to SQS.
3. A consumer processes the message and marks the notification `SENT` (AWS Lambda in production; local worker in dev).
4. The bell and `/notifications` page only show `SENT` / `READ` notifications.

### Fallback when SQS is unavailable

If `SQS_NOTIFICATION_QUEUE_URL` or AWS credentials are missing, the API still creates the notification row and marks it `SENT` immediately so the app keeps working.

### Required env var

```bash
SQS_NOTIFICATION_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/shiftops-notifications-queue
```

Also required for enqueue/worker: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`.

Validate setup:

```bash
cd backend
python scripts/validate_sqs_setup.py
```

### Local / dev demo

Run three terminals:

```bash
# Terminal 1 — worker (continuous polling)
cd backend
python scripts/notification_worker.py

# Terminal 2 — API
cd backend
uvicorn app.main:app --reload

# Terminal 3 — frontend
cd frontend
npm run dev
```

Trigger an action (publish schedule, approve time off, shift swap, document upload) and confirm the worker logs delivery and the UI shows the notification.

### Production (deployed)

```text
Vercel → Render API → SQS → Lambda (shiftops-notification-consumer) → Supabase
```

- The Render API enqueues `SEND_NOTIFICATION` jobs to `shiftops-notifications-queue`.
- **AWS Lambda** is the production consumer — do **not** run `notification_worker.py` against the production queue.
- DLQ is configured on the main queue; Lambda uses **Report batch item failures** for retries.

**Validate production (no local worker):**

```bash
# 1. Confirm local worker is stopped
pgrep -fl notification_worker || echo "OK — no local worker"

# 2. API + frontend smoke (includes publish → notifications on prod)
./scripts/smoke-production.sh

# 3. Optional — CloudWatch: Lambda → shiftops-notification-consumer → Monitor → View logs
#    Look for outcome=SENT after a publish or time-off action
```

**Emergency / dev fallback** (only if Lambda is down — never run alongside Lambda on the same queue):

```bash
cd backend
python scripts/process_notifications_once.py
```

### Lambda SQS consumer

Handler: `app.lambda_handlers.sqs_notification_handler.handle_sqs_event`

**Build deployment zip (local):**

```bash
cd backend
chmod +x scripts/build_lambda_package.sh
./scripts/build_lambda_package.sh
```

Output: `backend/dist/lambda_notification_consumer.zip`

**Lambda settings (AWS Console):**

| Setting | Value |
|---------|--------|
| Function | `shiftops-notification-consumer` |
| Runtime | Python 3.12 (x86_64) |
| Handler | `app.lambda_handlers.sqs_notification_handler.handle_sqs_event` |
| Timeout | 60 seconds |
| Memory | 256–512 MB |
| Env `DATABASE_URL` | Same Supabase URL as Render |
| Env `ENVIRONMENT` | `production` |
| Trigger | SQS `shiftops-notifications-queue` |
| Queue visibility timeout | 120 seconds |
| Event source | **Report batch item failures** enabled |
| DLQ | Configured on main queue |

**Local handler test:**

```bash
cd backend
pytest tests/test_lambda_notification_handler.py -q
python scripts/invoke_lambda_handler_local.py tests/fixtures/sqs_lambda_event.json
```

After code changes, rebuild the zip and upload a new version in the Lambda console.

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_lambda_package.sh` | Build `dist/lambda_notification_consumer.zip` for AWS |
| `scripts/invoke_lambda_handler_local.py` | Invoke handler locally with a JSON SQS event |
| `scripts/validate_sqs_setup.py` | Verify AWS SQS permissions and queue URL |
| `scripts/validate_notification_queues.py` | Read-only main queue + DLQ depth check |
| `scripts/notification_worker.py` | Continuous local/dev worker (blocked when `ENVIRONMENT=production`) |
| `scripts/process_notifications_once.py` | One-shot manual queue processing (same production guard) |

### Single consumer rule

Only **one** process should poll `shiftops-notifications-queue` in production:

| Consumer | When to use |
|----------|-------------|
| **AWS Lambda** (`shiftops-notification-consumer`) | Production — always on |
| `notification_worker.py` | Local dev only (`ENVIRONMENT=development`) |
| `process_notifications_once.py` | Emergency fallback when Lambda is disabled |

Local scripts **refuse to start** when `ENVIRONMENT=production` and SQS is configured. Use `--force` only for emergency debugging with Lambda disabled.

Check queue health (read-only):

```bash
cd backend
python scripts/validate_notification_queues.py
```

### Failure handling and retries

| Scenario | API / DB behavior | SQS / Lambda behavior |
|----------|-------------------|------------------------|
| SQS not configured | Notification marked `SENT` immediately | Not sent |
| SQS enqueue fails | Notification marked `SENT` immediately (fallback) | Not sent |
| Invalid queue payload | Logged | Message deleted (success from Lambda) |
| Delivery fails, `FAILED` row saved | `FAILED` + `error_message`, `retry_count` incremented | Message deleted |
| Delivery fails, cannot save `FAILED` | Stays `PENDING` | Lambda returns `batchItemFailures` → SQS retries |
| Duplicate delivery after `SENT` | No change (`ALREADY_DELIVERED`) | Message deleted |
| Retries exhausted | Row may stay `FAILED` or `PENDING` | Message moves to **DLQ** (check with `validate_notification_queues.py`) |

**Lambda retry flow:** visibility timeout 120s, Lambda timeout 60s, partial batch failures enabled. A failed record is retried without re-processing successful records in the same batch.

Failed deliveries store `error_message` and `retry_count` on the notification row for debugging. An empty DLQ under normal traffic means retries are succeeding or poison messages are not accumulating.
