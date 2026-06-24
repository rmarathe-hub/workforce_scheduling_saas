# Workforce Scheduling SaaS (ShiftOps)

Multi-tenant workforce scheduling SaaS — FastAPI backend + React frontend.

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

```
backend/
  app/
    main.py          # FastAPI app + CORS + /health
    config.py        # env settings
    database.py      # SQLAlchemy session
    models/          # users
    routes/auth.py   # register, login, me
    auth/            # JWT, password hashing, dependencies
    schemas/         # Pydantic request/response models
  alembic/           # migrations
  tests/
```

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

**Backend coverage includes:** auth/session, RBAC, multi-tenant isolation, org resources, availability, time-off, scheduling CRUD, schedule generation, conflict detection, publish workflow, and integration flows.

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

### Playwright production smoke (Day 33)

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

### GitHub Actions CI (Day 32)

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

## Observability (Day 34)

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
| `scripts/notification_worker.py` | Continuous local/dev worker |
| `scripts/process_notifications_once.py` | One-shot manual queue processing |

### Failure handling (Day 31)

| Scenario | API / DB behavior | SQS message |
|----------|-------------------|-------------|
| SQS not configured | Notification marked `SENT` immediately | Not sent |
| SQS enqueue fails | Notification marked `SENT` immediately (fallback) | Not sent |
| Invalid queue payload | Logged; message deleted | Deleted |
| Delivery processing fails | Notification marked `FAILED` with `error_message`, `retry_count` incremented | Deleted |
| DB unavailable while marking `FAILED` | Notification stays `PENDING` | Left on queue for retry |

Failed deliveries store `error_message` and `retry_count` on the notification row for debugging.
