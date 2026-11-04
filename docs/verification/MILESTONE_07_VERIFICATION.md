# Milestone 07 verification

Date: **4 November 2026**, Europe/Paris. Status: **implemented, verified and running locally**. Scope stops at Milestone 07.

## Result

Home offers a real persisted daily French plan. Learn offers three-card vocabulary review, secure answer feedback, backend scheduling, next due dates and actual history. Plans use the existing saved target, level, timezone, focus, unfinished lessons and unresolved recorded mistakes. No model generates or grades the plan/cards. Existing tutor and speech records provide linked practice and trusted completion.

The five navigation destinations and white/purple design are preserved. Exactly A1–C2 are supported. Levels never change automatically. All ten A1 lessons remain **draft** in main and preview; ordinary learners receive tutor/speaking alternatives rather than draft lesson/card links.

## Architecture and files

Read [architecture](../architecture/adaptive-learning-engine.md), [daily plan policy](../learning/daily-study-plan.md), [scheduler](../learning/spaced-repetition.md), and [security](../security/adaptive-learning-security.md).

Created backend files:

- `app/study_models.py`, `app/study_schemas.py`, `app/api/v1/study.py`.
- `app/services/study_clock.py`, `study_content.py`, `review_grading_service.py`, `review_scheduler.py`, `spaced_repetition_service.py`, `daily_learning_service.py`.
- `alembic/versions/20261104_0008_adaptive_learning.py`.
- `tests/test_study.py`, `tests/test_study_postgres.py`.
- Guarded test helpers `scripts/study_e2e_server.py`, `prepare_study_browser.py`, `verify_study_live.py`.

Modified backend files: `app/main.py` (router/private headers), `alembic/env.py` (model registration), `requirements.txt` (pinned IANA `tzdata`), `app/services/learning_service.py` (optional shared-transaction start; existing default/API behavior retained).

Created frontend files: `lib/study.ts`, `components/daily-plan.tsx`, `components/vocabulary-review.tsx`, `app/review/page.tsx`, `app/review/sessions/[sessionId]/page.tsx`, `e2e/study.spec.ts`.

Modified frontend files: Home `app/dashboard/page.tsx`, Learn `app/courses/page.tsx`, `app/progress/page.tsx`, and `app/globals.css`. No primary navigation destination was added. The new dynamic review route uses Suspense/useParams consistently with the installed Next.js Cache Components behavior.

Documentation: this file, the four linked design/security documents, README, and the existing [A1 readiness report](../content/reviews/A1_REVIEW_READINESS.md) with an additional observed draft-import limitation. Evidence files include `MILESTONE_07_BACKEND.xml`, `MILESTONE_07_PRESERVATION.json`, `MILESTONE_07_LIVE.json`, `MILESTONE_07_A1_MAIN.json`, `MILESTONE_07_A1_PREVIEW.json`, `MILESTONE_07_CONTENT_LIMITATIONS.json`, and screenshots in `milestone-07/`.

## Migration and database

Inspected prior head: `20261102_0007`. New head: **`20261104_0008`**. Main and preview both successfully upgraded to that revision.

| New table | Purpose |
|---|---|
| `daily_learning_plans` | User/local-date/level identity, saved timezone/target, generation and status |
| `daily_learning_activities` | Ordered estimated tasks, actual owned links, evidence and completion |
| `spaced_repetition_cards` | Stable user/sense/level/type identity and current versioned schedule |
| `vocabulary_review_sessions` | Owned resumable bounded review selection |
| `vocabulary_review_session_items` | Immutable ordered question/answer/version snapshots; private keys |
| `spaced_repetition_reviews` | Immutable graded attempts and before/after scheduling audit |

Uniqueness protects plan identity, card identity, active user/level sessions, answer request IDs and individual session-item attempts. Composite review FKs enforce ownership and item/session/card context. Due/history/plan indexes and level/status/range constraints are included. Existing resource links retain legacy FKs plus service-side ownership checks. No old table or historical progress is backfilled.

Real PostgreSQL tests create randomly named `fluentloop_m07_*` databases. Tested a direct fresh-to-head upgrade, a populated pre-M07 upgrade, safe isolated downgrade/re-upgrade, and exact pre-M07 row fingerprints. The populated fixture includes a user/profile/preferences, auth session, lesson progress/session, AI message and uncertain speech history. No rollback experiment runs on main/preview. Isolated test databases are retained for inspection.

## Algorithms and completion

Ranking version `priority-v1`: due cards 100; unfinished lessons 90; unresolved current-source lesson mistakes 80; authorized new vocabulary/material 60; existing tutor/speaking practice 10–35 according to saved focus/goal. Use the latest 200 actual attempts, and stop an old error streak when a later correct attempt resolves that source exercise. Keep prior attempts intact. Do not infer a grammar topic from a lesson-only link. Reasons and actual attempt references explain remedial recommendations.

Allocation: up to two minutes for three cards, five for one lesson candidate and ten per distinct conversation. It fits the target where realistic tasks permit; otherwise shows an honest shorter estimate. Examples: 2 + 5 + 4 + 4 = 15 minutes for authorized review/lesson/practice; 8 + 7 for permitted practice without curriculum; only 20 of a 30-minute target when the two real practice options are all that exist. Estimated time is never recorded as actual study time.

Scheduler `fl-sm2-v1` is explicitly SM-2-inspired, not original SM-2. New cards are due now. Correct reviews schedule 1 day, then 3 days, then rounded interval × adjusted ease (1–365 days). Ease begins at 2.5 and stays within 1.3–3.0; correct easy/difficult changes it ±0.15. Incorrect answers reset repetitions, increment lapses, subtract 0.2 ease and schedule ten minutes later regardless of rating. Viewing a card does not schedule it. Each assigned card appears once in a session.

Typed grading preserves accents while normalizing NFC, case, whitespace, supported apostrophes/dashes and terminal punctuation. Accept only stored French equivalents from currently authorized records with the same English meaning; do not invent synonyms. Reject authoritative frontend grading flags. Wrong + easy remains wrong. Hold session/card locks and commit attempt plus schedule together. Exact UUID retries replay the existing result; conflicting duplicates cannot schedule twice.

Completion requires actual linked state: a finished review with an answer, a completed lesson after activity start, a successful tutor reply, or a successful transcribed/user-confirmed speech turn. Merely opening a page, silence, failed inference or text fallback for speaking does not qualify. Home reconciles saved state on return. Explicit completion checks the same policy. Regeneration is an explicit action restricted to entirely unstarted plans and retains cancelled older generations.

UTC timestamps and the saved IANA timezone determine the local study date; invalid legacy zones fall back to documented UTC. DST repeated hours do not create a second plan. A level switch preserves all previous-level cards, plans and history. There is no automatic level promotion.

## API endpoints

All paths use `/api/v1`, authenticated ownership and private no-store responses. Mutations require existing CSRF/origin protection and per-user rate limits. GETs are also bounded by a study read limit.

| Method | Path |
|---|---|
| GET | `/study/today` (persisted plan or null) |
| POST | `/study/today/generate` (UUID and optional explicit regeneration) |
| GET | `/study/plans`, `/study/plans/{plan_id}` |
| GET | `/study/recommendations` |
| POST | `/study/activities/{activity_id}/start` |
| POST | `/study/activities/{activity_id}/complete` |
| GET | `/review/due` |
| POST | `/review/sessions` |
| GET | `/review/sessions/{session_id}` |
| POST | `/review/sessions/{session_id}/answers` |
| POST | `/review/sessions/{session_id}/complete` |
| GET | `/review/progress`, `/review/history` |

No client user ID or preview switch is accepted. Recheck publication/RBAC on plans, starts, review questions and submissions. Revoked source text/keys disappear while historical correctness/scheduling metadata remains. Existing conversation source checks are reused for linked tutor/speech practice. The planner never contacts Ollama or sends profile secrets.

## Actual test results

| Check | Executed result |
|---|---|
| Full backend in native environment | **203 passed, 0 skipped**, 2 pre-existing dependency deprecation warnings; 143.42 seconds. [JUnit](MILESTONE_07_BACKEND.xml). |
| New M07 cases | 42 unit/service cases plus 2 real PostgreSQL tests, included in the 203. Cover scheduling boundaries, alternatives/normalization, actual mistakes and resolution, default/saved targets, offline planning, dates/DST, regeneration, six levels, isolation, permission revocation, rating separation and answer secrecy. |
| Existing native speech checks | 34 decoding/ASR-policy/voice-style cases included in the full native-environment run. No model thresholds or speech privacy behavior changed. |
| PostgreSQL integration | Both M07 tests passed, plus existing AI/speech PostgreSQL tests in the full suite. Concurrent plan requests return one identity; concurrent answer UUID retries return one attempt/schedule; forced failure after SQL flush rolls back attempt and card together. Saved state resumes in another HTTP client/connection. |
| ESLint / TypeScript | Passed on final frontend source. |
| Production build | Passed; **35 pages** generated and the new dynamic review route prerenders correctly behind Suspense. |
| New real-API browser acceptance | **2 passed** against FastAPI + actual isolated PostgreSQL + real Redis: three answers (correct/incorrect/correct), difficulty/correctness separation, double-click protection, actual due feedback, review completion, actual lesson grading/completion, Home reconciliation, refresh/logout/login resume, A2 switch retaining A1 history, and ordinary-learner draft denial. |
| New network-failure UI case | **1 passed**, explicitly simulating only the plan request failing; existing practice navigation remains usable. |
| Existing frontend regression group | **13 passed**: text tutor, actual account registration/verification/onboarding/profile, learning, live lesson persistence/idempotency/owner denial, and five-destination responsive/focus/appearance checks. Some text-tutor/learning states use their existing mocked APIs; the report does not label those as genuine model inference. |
| Existing speech browser cases | **8 unique cases passed** across the initial five passes and a separate successful three-case rerun. The initial single batch reached the unchanged speech quota; the isolated fake-inference test API was restarted for the remainder. No application quota or validation was disabled. Includes uncertain editing/confirmation/original replay, re-record, private audio deletion, history, owner denial and track cleanup. |
| Total browser coverage | **24 unique cases passed**, across the groups above. This is not a claim that one unconfigured command ran every opt-in test in one batch. |
| Real linked tutor/speech inference | Passed via `verify_study_live.py`: real Ollama `llama3.2:3b`, human French Ogg → actual Faster-Whisper Base CPU → `bonjour`, actual French tutor reply → Piper RIFF audio (**74,284 bytes**), linked activity completion, partial plan persistence and login resume. Both inference requests succeeded on their first attempt. [Evidence](MILESTONE_07_LIVE.json). |
| Main/preview Docker | Both backend/frontend image builds and additive upgrades passed. All **12 services running/healthy**. APIs ready and frontend pages return 200 at ports 8000/8001 and 3000/3001. Existing private speech workers were preserved. |

The browser regression found and fixed a real review UI race: feedback appeared before the refreshed session arrived. Next is now disabled until that saved state is ready. The acceptance test deliberately holds the real refresh response and asserts this behavior. It also identified valid same-meaning vocabulary alternatives, which now come only from authorized stored records.

Screenshots at widths 320/390/1440 verify focused card controls, no horizontal overflow and the existing responsive design. Desktop/mobile screenshots were visually inspected. Browser microphone tests use Chromium's fake device and controlled inference. The separate HTTP live test uses real recorded French/model/TTS inference; neither test is described as a physical-device microphone check.

## Existing user/data preservation

[Before/after fingerprints](MILESTONE_07_PRESERVATION.json) cover all **52 pre-existing tables** in each deployed database, including learning/AI/speech history. Main: **all 52 full-table hashes and row counts unchanged**. Preview: **51/52 hashes unchanged, all 52 row counts unchanged**. Only preview `lexemes` differs after its existing startup content import; that importer refreshes the `avoir` timestamp. Because the baseline is a table hash, it cannot provide a complete before-image field diff of that one table.

User/password/profile/preferences/auth-session/progress/attempt/AI/speech-history hashes are unchanged in both stacks. Six new tables were added. No real account was used for test mutations, no old records were deleted, and no volume was reset. Migration head is `20261104_0008` in both stacks. Each still contains exactly **10 draft lessons and 0 published lessons**.

## Content and other limitations

- The existing A1 audit still reports main A1-003's extra grammar link and both deployments' A1-009 missing example links. See [main](MILESTONE_07_A1_MAIN.json) and [preview](MILESTONE_07_A1_PREVIEW.json). This technical audit is not green and is not a publication approval.
- Preview testing additionally exposed five existing noun-import artifacts caused by the older article-prefix regex, including `une table → e table` and `les parents → s parents`. [Read-only findings](MILESTONE_07_CONTENT_LIMITATIONS.json) and the updated A1 review packet identify them. M07 does not rewrite those lexical IDs, the importer, source drafts or approval records. Draft-derived cards remain unreviewed; ordinary learners cannot access them. Linguistic/import reconciliation is required before publication.
- The scheduler is a bounded deterministic heuristic, with no learner-calibrated retention guarantee. Meaning-only translation cards do not assess contextual gender/register. Topic-level remediation is intentionally omitted where no reliable objective association exists.
- With no authorized curriculum and inference offline, a plan can be saved/resumed but model-dependent practice cannot complete until its services recover. No fake offline lesson is substituted.
- Physical microphone permissions, mobile soft keyboard and device-specific recording behavior still need manual device checks. Automated viewport tests and a real recorded fixture are the evidence actually available.
- Docker frontend entrypoints remain the project's existing development server configuration; a separate production build was verified. This milestone does not claim public production hosting or hardening.
- Independent French/pedagogy/exercise/rights review remains pending. No author or AI attestation was fabricated. Milestone 08 was not started.

## Exact Windows PowerShell verification commands

Run from `D:\shyam\Projects\FluentLoop AI` using the existing environments/cached models. These are local development URLs. The opt-in PostgreSQL tests use isolated databases; never substitute main/preview URLs for their dedicated test URLs.

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
$env:AI_TEST_DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/fluentloop_m05_verify'
$env:SPEECH_TEST_DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/fluentloop_m06_verify'
$env:STUDY_TEST_ADMIN_DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/postgres'
.\.venv-speech\Scripts\python.exe -m pytest backend/tests -ra -o addopts='' --junitxml=docs/verification/MILESTONE_07_BACKEND.xml

Push-Location frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
Pop-Location

$dockerForStudy = 'C:\Users\Shyam\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
& $dockerForStudy compose ps --format '{{.Service}} {{.State}} {{.Health}}'
& $dockerForStudy compose -f docker-compose.preview.yml -p fluentloop-preview ps --format '{{.Service}} {{.State}} {{.Health}}'
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
Invoke-RestMethod http://localhost:8001/api/v1/health/ready
```

For the new real PostgreSQL browser acceptance, use the existing migrated `fluentloop_m07_browser` database and a separate terminal for the guarded API. The test harness preserves existing test records and creates fresh accounts before each full acceptance run. It uses real Redis with a fresh test-instance namespace and the unchanged limiter rules.

```powershell
$env:PYTHONPATH = 'backend'
$env:DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/fluentloop_m07_browser'
$env:REDIS_URL = 'redis://127.0.0.1:6379/5'
$env:STUDY_E2E_TEST_SERVER = '1'
$env:APP_ENV = 'development'
$env:ENABLE_DRAFT_LEARNING_PREVIEW = 'true'
$env:FRONTEND_ORIGIN = 'http://127.0.0.1:3017'
$env:CORS_ORIGINS = '["http://127.0.0.1:3017"]'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'llama3.2:3b'
$env:SPEECH_WORKER_URL = 'http://127.0.0.1:8095'
$env:SPEECH_WORKER_TOKEN = 'isolated-speech-test-key'
$env:SPEECH_STORAGE_PATH = Join-Path (Get-Location).Path '.speech-data/m07-browser'
.\.venv312\Scripts\python.exe -m uvicorn scripts.study_e2e_server:app --app-dir backend --host 127.0.0.1 --port 8017 --no-access-log
```

In another terminal, set the same `PYTHONPATH`, `DATABASE_URL`, test flag, development and preview values, then:

```powershell
.\.venv312\Scripts\python.exe backend/scripts/prepare_study_browser.py
Push-Location frontend
$env:STUDY_E2E_REAL_API = '1'
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3017'
$env:PLAYWRIGHT_API_BASE_URL = 'http://127.0.0.1:8017/api/v1'
$env:UI_SCREENSHOTS = '1'
npx.cmd playwright test e2e/study.spec.ts --workers=1
Pop-Location
```

Playwright starts/reuses the test frontend with its matching API base. Do not share a running frontend dev server compiled against a different test API. For the real model smoke, run the existing local Ollama model and an isolated native worker in another terminal (the test key below is never a main/preview key):

```powershell
$env:PYTHONPATH = 'backend'
$env:SPEECH_MODEL_PATH = Join-Path (Get-Location).Path '.speech-models'
$env:SPEECH_ASR_MODEL = 'base'
$env:SPEECH_WORKER_TOKEN = 'isolated-speech-test-key'
$env:OPENBLAS_NUM_THREADS = '2'
.\.venv-speech\Scripts\python.exe -m uvicorn app.speech.worker:app --app-dir backend --host 127.0.0.1 --port 8095 --no-access-log
```

With the guarded test API still running and the isolated `DATABASE_URL` / `STUDY_E2E_TEST_SERVER` / `PYTHONPATH` set:

```powershell
.\.venv312\Scripts\python.exe backend/scripts/verify_study_live.py
```

Existing browser regression files were executed against their original guarded `scripts.speech_e2e_server:app` at port 8016, with `AI_E2E_TEST_SERVER=1`, isolated M06 database, matching frontend origin/API base, and `SPEECH_E2E_REAL_API=1` / `AI_E2E_REAL_API=1`. The live M04 case additionally used fresh isolated accounts and actual exercise option IDs. Keep those expectations in local test fixtures, never learner endpoints. Split speech groups when the existing quota is exhausted rather than changing validation or production limits.

## Manual checks

1. Open main `http://localhost:3000` or authorized preview `http://localhost:3001`, sign in and keep the saved CEFR level/target unchanged.
2. Home → Create today’s plan. Confirm the target, estimates, reasons, status and one Start/Continue action. Refresh and confirm the same plan remains.
3. An ordinary learner with only draft A1 content should see permitted tutor/speaking alternatives, no draft lesson links and no draft cards. Learn → Review vocabulary honestly shows empty availability.
4. With an authorized preview account, start vocabulary review. Check draft labeling, answer three cards with one intentional mistake, select easy on that mistake, and confirm it remains incorrect with an earlier due time. Double-click Check: one result only.
5. Finish review, return Home and verify its activity completed while remaining work stays pending. Complete the linked lesson or a real tutor/speech interaction and return again; opening the page alone must not complete it.
6. Refresh and sign out/in. Confirm review history/due dates and partial plan persist. Change to A2, generate its separate plan, then inspect the preserved A1 review history.
7. On mobile widths, use keyboard focus/answer controls and verify all five navigation destinations. On a physical device, separately test microphone permission, uncertain transcript correction/explicit confirmation and French playback.
8. Confirm existing profile name, progress, text/voice history, privacy settings and sessions remain available. All ten A1 lessons must still show draft in authorized preview and remain hidden from ordinary learners.

Suggested future Milestone 08 scope, **not implemented**: reviewed curriculum/importer reconciliation and explicit exercise-to-learning-objective mappings before adding more sophisticated remediation or retention calibration.
