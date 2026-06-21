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
pytest
```

If `TEST_DATABASE_URL` is unset, tests fall back to `DATABASE_URL` from `.env`.

| Command | Purpose |
|---------|---------|
| `pytest` | All local integration tests |
| `pytest -m "not e2e and not future"` | Skip deployed smoke + future engine placeholders |
| `pytest -m e2e` | Deployed API smoke tests (requires `E2E_API_BASE_URL`) |

**Deployed API smoke tests:**

```bash
cd backend
export E2E_API_BASE_URL="https://workforce-scheduling-api.onrender.com"
pytest -m e2e
```

Uses unique `e2e-*@example.com` emails and org names so it does not collide with demo data.

**Environment variables:**

| Variable | Used by | Description |
|----------|---------|-------------|
| `TEST_DATABASE_URL` | pytest | Optional separate DB for local tests |
| `E2E_API_BASE_URL` | pytest `-m e2e` | Deployed Render API base URL |

### Frontend build

```bash
cd frontend
npm run build
```

### Playwright E2E (deployed frontend)

```bash
cd frontend
npm install
npx playwright install chromium
export E2E_FRONTEND_URL="https://workforce-scheduling-saas.vercel.app"
npm run test:e2e
```

Smoke flow: register → manager schedule → quick setup (location + role).

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `E2E_FRONTEND_URL` | Deployed Vercel app URL (defaults to `http://localhost:5173`) |

Important UI elements use `data-testid` attributes (`register-form`, `login-form`, `dashboard`, `create-location-button`, etc.) for stable selectors.

### Scheduling engine (Week 2+)

`conflict_detector.py` and `schedule_generator.py` are not implemented yet. Placeholder tests live in `backend/tests/test_scheduling_engine.py` and are marked `future` (skipped until Week 2).
