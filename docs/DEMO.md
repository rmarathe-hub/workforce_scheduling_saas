# ShiftOps — portfolio demo guide

Use this for interviews, LinkedIn posts, and recruiter screen shares.  
**Live app:** https://workforce-scheduling-saas.vercel.app  
**API:** https://workforce-scheduling-api.onrender.com

---

## Pre-demo checklist (2 minutes)

```bash
# From repo root — confirm prod is healthy
curl -s https://workforce-scheduling-api.onrender.com/health | python3 -m json.tool

# No local worker competing with Lambda
pgrep -fl notification_worker || echo "OK — no local worker"

# Optional: queue depth (needs AWS creds in backend/.env)
cd backend && python scripts/validate_notification_queues.py
```

Expect `/health`: `database: ok`, `sqs_configured: true`, `s3_configured: true`.

Have open in browser tabs (before screen share):

1. Production app (logged out)
2. AWS Console → Lambda → `shiftops-notification-consumer` → **Monitor → View CloudWatch logs**
3. AWS Console → SQS → `shiftops-notifications-queue` (optional)

---

## 3-minute demo script

**Org name idea:** *Boston Fitness Studio* (or register fresh — smoke tests use `Smoke Test Org …` timestamps).

| Time | What you show | What you say |
|------|----------------|--------------|
| **0:00–0:30** | Login / register as owner → manager dashboard | “ShiftOps is multi-tenant workforce scheduling — owners set coverage, generate schedules with conflict checks, and publish to employees.” |
| **0:30–1:30** | Manager schedule: add coverage if needed → **Generate week** → **Validate** → **Publish** | “Publish is the key event — it writes to Postgres, logs activity, and enqueues an async notification job to SQS. The API returns fast; delivery is decoupled.” |
| **1:30–2:15** | **Activity log** (`/manager/activity`) → **Notifications** (`/notifications`) — show bell unread count | “Within about a minute, AWS Lambda consumes the SQS message and marks the notification SENT. No background worker on Render — Lambda is the production consumer.” |
| **2:15–2:45** | Log in as **employee** → **My shifts** + notifications | “Employees only see published shifts and SENT notifications — RBAC and status filtering on the API.” |
| **2:45–3:00** | Flash **CloudWatch** log: `outcome=SENT` (or architecture diagram in README) | “Stack: Vercel, Render, Supabase, S3 for documents, SQS + Lambda for async delivery. CI runs pytest and Playwright smoke against prod.” |

### Optional 60-second add-ons (if asked)

- **Documents:** Manager → employee documents → upload (S3 presigned URL flow).
- **Time off:** Employee requests → manager approves → second notification via same SQS → Lambda path.
- **Analytics cards** on manager dashboard after publish (published shift count).

---

## Screenshot checklist (for resume / portfolio site)

Capture these once and reuse:

| # | Screenshot | Where |
|---|------------|--------|
| 1 | Manager schedule with published week | `/manager/schedule` after publish |
| 2 | Notification bell + list with “Schedule published” | `/notifications` or dashboard summary |
| 3 | Activity log entry | `/manager/activity` |
| 4 | CloudWatch log line | `Processed SQS record … outcome=SENT` |
| 5 | Architecture diagram | README → Architecture (export Mermaid or redraw) |
| 6 | GitHub Actions green | Repo → Actions → latest `Backend tests` |

**CloudWatch path:** AWS → Lambda → `shiftops-notification-consumer` → Monitor → View logs in CloudWatch → filter `outcome=SENT`.

---

## Resume bullets

Pick 2–3 for a new-grad resume or LinkedIn projects section.

**Full-stack + async (recommended):**

> Built **ShiftOps**, a multi-tenant workforce scheduling SaaS (FastAPI, React, PostgreSQL) with schedule generation, conflict detection, RBAC, and document storage on **AWS S3**; deployed frontend on **Vercel** and API on **Render**.

**Async / cloud (Lambda story):**

> Implemented **async in-app notifications** with **AWS SQS and Lambda**, decoupling delivery from the FastAPI API; configured DLQ, partial batch failures, and idempotent processing shared between local workers and the Lambda handler.

**Quality / ops:**

> Added **GitHub Actions CI**, health/readiness endpoints, structured logging, and **Playwright production smoke tests** against live Vercel and Render deployments.

**One-liner (projects table):**

> ShiftOps — scheduling SaaS with SQS/Lambda notifications, S3 documents, Supabase Postgres, CI + prod smoke tests. [Live demo](https://workforce-scheduling-saas.vercel.app)

---

## Interview talking points

1. **Why SQS + Lambda instead of a Render background worker?**  
   Cheaper at low volume, scales independently, clear separation of sync API vs async delivery; Lambda only runs when messages exist.

2. **How do you avoid double delivery?**  
   Single consumer in prod (Lambda only); local scripts refuse to run when `ENVIRONMENT=production`; processor treats already-`SENT` rows as `ALREADY_DELIVERED`.

3. **What happens when processing fails?**  
   Row marked `FAILED` with `error_message` when possible; otherwise `batchItemFailures` for SQS retry → DLQ after max receives.

4. **Multi-tenancy:**  
   `organization_id` on rows; JWT + membership roles (`OWNER` / `MANAGER` / `EMPLOYEE`); API checks on every route.

5. **Testing:**  
   ~200+ backend pytest tests, moto/local SQS for queue tests, Lambda handler unit tests, Playwright E2E locally and against prod.

---

## AWS cost sanity check (typical portfolio traffic)

| Service | Rough cost at demo/low traffic |
|---------|--------------------------------|
| **Lambda** | Free tier: 1M requests/month; notification handler is short (~seconds) |
| **SQS** | Free tier: 1M requests/month; pennies at hobby scale |
| **S3** | Storage +少量 GET/PUT; demo docs negligible |
| **Supabase** | Free tier for Postgres |
| **Render** | Free or ~$7/mo web service |
| **Vercel** | Free tier for hobby frontend |

**Total for interviews/demos:** typically **$0–10/month** unless Render is on a paid plan.

---

## Quick commands reference

```bash
# Full production smoke (API + frontend)
./scripts/smoke-production.sh

# Notification test subset (local)
cd backend && pytest tests/test_notification_queue.py \
  tests/test_notification_reliability.py \
  tests/test_notification_delivery_pipeline.py \
  tests/test_lambda_notification_handler.py \
  tests/test_consumer_safety.py -q

# Rebuild Lambda zip after handler changes
cd backend && ./scripts/build_lambda_package.sh
```
