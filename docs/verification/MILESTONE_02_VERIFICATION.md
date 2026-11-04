# FluentLoop AI Milestone 02 Verification Report

## Scope

Milestone 02 adds secure learner registration and authentication, email verification, profile and preferences APIs, onboarding, protected learner pages, sessions, and account settings. It does not include Milestone 03 course or AI tutor functionality.

## Validation results

All checks below were run locally on Windows with Docker Desktop:

- Backend regression suite (run from `backend/`): `..\.venv312\Scripts\python.exe -m pytest -q`
  - Result after the development registration limit change: **23 passed**. Pytest reported two dependency deprecation warnings; neither affected the test result.
- Frontend lint: `npm run lint`
  - Result: **passed**.
- Frontend type check: `npm run typecheck`
  - Result: **passed**.
- Frontend production build: `npm run build`
  - Result: **passed**; all 11 application routes were generated.
- Browser flow: `npm run test:e2e`
  - Result after the development registration limit change: **2 passed**. Coverage includes retry-message handling, registration, Mailpit email verification, invalid and valid login, onboarding completion and persisted-answer reload, profile editing, settings, logout, and protected-route redirection.
- Compose configuration: `docker compose config --quiet`
  - Result: **passed**.
- Docker rebuild/restart: `docker compose up -d --build backend frontend`
  - Result: **passed**. Backend, frontend, PostgreSQL, Redis, and Mailpit all reported healthy afterward.
- Database migration: `docker compose exec -T backend alembic current`
  - Result: `20261101_0001 (head)`.
- Host HTTP checks after the rebuild:
  - `http://localhost:3000` — **200**
  - `http://localhost:8000/docs` — **200**
  - `http://localhost:8000/api/v1/health/live` — **200**
  - `http://localhost:8000/api/v1/health/ready` — **200**, with PostgreSQL and Redis both reported `connected`.

The browser tests used a dedicated PostgreSQL database and separate Redis container, with Mailpit for verification email. They did not use the application database or Redis counters. The isolated test database is retained with its test accounts; the application database and Redis counters were preserved.

## Local development registration limit follow-up

- The registration endpoint retains a limit of **5 requests per hour** unless `APP_ENV=development`.
- In development, `DEV_REGISTER_LIMIT` controls the hourly limit and defaults to **30** in `.env.example` and Docker Compose.
- Settings tests confirm development uses the configured value and production, test, and staging use 5. The endpoint test confirms its configured hourly limit is passed to the Redis limiter.
- After rebuilding the backend, its runtime settings reported `APP_ENV=development`, `DEV_REGISTER_LIMIT=30`, and an effective limit of 30.
- A real registration submitted through the browser at `http://localhost:3000/register` succeeded. The new user was present in the application database and its verification email appeared in Mailpit. The main database user count before this registration was zero; the newly created test account was retained.
- The pre-existing shared Redis registration key remained intact across the backend restart. Its count increased only by the successful registration; no Redis keys or user records were cleared.

## Operational and security notes

- `CORS_ORIGINS` is supplied as a JSON array with explicit local frontend origins; wildcard origins are not used.
- The backend container health check uses Python's standard-library HTTP client rather than `curl`.
- The frontend depends on the backend health check, so it starts only after backend readiness succeeds.
- PostgreSQL and Redis readiness is checked by `/api/v1/health/ready`; liveness remains independent of those dependencies.
- Docker ports are bound to loopback. Production deployment still requires TLS, secure cookies, explicit origins, and production SMTP configuration.
- The CI workflow was added but was not run on GitHub in this verification session.

## CEFR level selection update

- Supported values are exactly `a1`, `a2`, `b1`, `b2`, `c1`, and `c2`; new preferences and onboarding default to A1.
- Migration `20261101_0002` applied successfully to the Compose application database and the retained isolated browser-test database. Both now report revision `20261101_0002 (head)`.
- Before migration, the application DB had one legacy Pre-A1 preference; afterward both existing preference rows are A1 and no target-level Pre-A1 values remain. In the isolated test DB, all five legacy Pre-A1 preferences became A1; existing B1/C1 records were retained, no target-level legacy values remain, and all seven pre-existing test accounts remained. The browser flow then added one test account; no records were deleted.
- Backend tests: **24 passed**. Coverage includes default A1, all six accepted and persisted levels, rejection of legacy/invalid values, onboarding persistence, dashboard difficulty context, dashboard/settings changes, and cross-user isolation.
- Frontend lint, TypeScript, and production build: **passed**.
- Playwright: **2 passed**. The browser flow asserts exactly six onboarding and Settings choices, selects B1 during onboarding, changes the level to A2 on the dashboard and C1 in Settings, and confirms the dashboard reflects the saved selection.
- Docker Compose configuration and all services: **healthy**. The app, Swagger docs, liveness, and readiness endpoints returned HTTP 200; readiness reported PostgreSQL and Redis connected.

The dashboard API exposes `learning_context.difficulty_level` from the saved preference for future lesson/exercise/conversation/pronunciation features. Those features and progress tracking remain unimplemented; changing the preference does not delete or reset account data.
