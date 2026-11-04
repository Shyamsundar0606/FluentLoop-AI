# Milestone 04 Verification

**Status:** Milestone 04 is verified locally. A persistent, isolated manual preview stack is running separately from the main application. This is not a production deployment certification. Milestone 05 has not started.

## Preserved main application

Before provisioning the manual preview, the main application reported 2 users, 10 A1 lessons (all draft), 0 published lessons, and Alembic `20261102_0004`. After setting up the preview and rebuilding only preview frontend, the main service remained healthy at `http://localhost:3000` and `http://localhost:8000`; its two accounts and all ten draft lessons remain intact. The main backend keeps `ENABLE_DRAFT_LEARNING_PREVIEW=false`. No main account role or database volume was modified.

## Isolated manual preview

The separate Compose project is `fluentloop-preview`, configured by [docker-compose.preview.yml](../../docker-compose.preview.yml). It has a dedicated persistent PostgreSQL volume, Redis, Mailpit, backend, and frontend. It binds only loopback ports:

- Preview frontend: http://localhost:3001
- Preview FastAPI docs: http://localhost:8001/docs
- Preview readiness: http://localhost:8001/api/v1/health/ready
- Preview PostgreSQL: `127.0.0.1:5433`
- Preview Redis: `127.0.0.1:6380`
- Preview Mailpit: http://localhost:8026

The isolated API runs with `APP_ENV=development` and `ENABLE_DRAFT_LEARNING_PREVIEW=true`. It still requires the existing authenticated `admin` role. It uses its own database, Redis, CORS allowlist, frontend origin, and distinct session/CSRF cookie names. The CSRF cookie name is configured in the preview frontend so state-changing learning calls remain protected without overwriting the main app's cookie.

The preview database has two dedicated, verified accounts: one `admin` developer and one ordinary `learner`. Both are onboarded, contain no relation to a main-app account, and were created only in the preview database. Keep their credentials in a password manager; they are supplied separately to the operator.

The preview importer created **10 A1 lessons**, all **draft**, and **0 published** lessons. All ten lessons appear in the developer's A1 course details with a per-lesson **Draft Preview · unreviewed** label. No content was published.

## Runtime verification

- Docker Linux engine: available.
- All five preview services (PostgreSQL, Redis, Mailpit, FastAPI, Next.js): **healthy**.
- Preview FastAPI live, ready, docs, and frontend: **HTTP 200**. Readiness reports PostgreSQL and Redis connected.
- Main frontend `http://localhost:3000`, main docs `http://localhost:8000/docs`, main live and ready checks: **HTTP 200**.
- Main and preview apps run simultaneously on distinct ports. Preview authentication uses distinct cookies and the browser-flow verification passed with the preview CORS configuration.
- Preview persistence uses a separate named volume. Stopping preview with `docker compose -p fluentloop-preview -f docker-compose.preview.yml down` retains it; do not use `-v` if preserving preview accounts/progress.

## Live browser and PostgreSQL verification

The browser integration test used the real preview frontend, FastAPI service, PostgreSQL database, and Redis. It verified:

1. The developer can sign in and sees the A1 course plus exactly 10 draft-preview lesson labels.
2. The developer starts a lesson session, submits a correct answer and an incorrect answer, refreshes, resumes, finishes, and sees **4/5 correct (80%)**.
3. After logout and login, the completed lesson and score remain in progress history and the dashboard. Metrics show one completed lesson, answered exercises, and an 80% average score.
4. Replaying a correct answer with its same idempotency key returns a replay without changing the score or adding an attempt.
5. The ordinary learner sees no A1 courses and receives HTTP 404 for the draft lesson, another user's session, and a protected answer request.

After two successful integration runs, PostgreSQL independently showed two completed sessions for the developer, ten attempts worth eight points, and one per-lesson progress row with two completions, best/latest score 80. The duplicate submissions did not add attempts. The ordinary learner had no sessions or progress.

## Automated checks

- Backend regression suite from Milestone 04: **36 passed**, with two existing dependency deprecation warnings.
- Frontend ESLint: **passed** with no warnings.
- TypeScript check: **passed**.
- Next.js production build: **passed**.
- The dedicated live Playwright test against the manual preview stack: **1 passed**. It covers the live flow, all ten draft labels, dashboard and progress persistence, idempotency, and ordinary-user denial.
- The standard Playwright suite previously reported **3 passed, 1 skipped**; its isolated live test is run separately with the dedicated test accounts.

## Scope and limitations

- This is a local development preview, not production hosting or independent curriculum approval.
- All A1 content remains draft. French-language, pedagogical, answer-key, and licensing review gates remain unchanged.
- No personal/main-app role was changed, no existing user data was cleared, and no Milestone 05 work was performed.
