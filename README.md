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
| `npm run test:e2e:smoke` | Production smoke subset only |
| `npm run test:all` | `build` + full E2E |

**Playwright coverage includes:** auth (positive/negative), protected routes, owner setup, coverage, generate, publish, conflicts, employee flows, RBAC (both directions), manager time-off/availability, navigation, and employee-published-shift handoff.

### Playwright production smoke

Runs against deployed frontend without starting local servers:

```bash
cd frontend
export E2E_SMOKE=1
export E2E_SKIP_WEBSERVER=1
export E2E_BASE_URL="https://workforce-scheduling-saas.vercel.app"
npm run test:e2e:smoke
```

| Variable | Description |
|----------|-------------|
| `E2E_BASE_URL` / `E2E_FRONTEND_URL` | Frontend URL (defaults to `http://localhost:5173`) |
| `E2E_SMOKE=1` | Run production smoke project only |
| `E2E_SKIP_WEBSERVER=1` | Do not auto-start backend/Vite |

### Pre-push checklist

1. `cd backend && pytest -m "not future"`
2. `cd frontend && npm run build`
3. `cd frontend && npm run test:e2e`
4. Optional deployed: `pytest -m e2e` and `npm run test:e2e:smoke` with env vars above

Important UI elements use `data-testid` attributes for stable selectors.
