# Milestone 08.2 — learning experience and local integration readiness

Verified locally on 2026-11-05 (Europe/Paris). This extends the existing M01–08.1
application. No commit, push, PR, merge, deployment, curriculum publication or
Milestone 09 work was performed. Existing uncommitted work was retained.

## Existing functionality and environment inspection

Inspected the M08/08.1 reports, curriculum snapshots, six exercise renderers,
grading/idempotency, authenticated preview permissions, M07 recommendations and
vocabulary scheduler, auth/mail flows, voice transcript confirmation, migrations,
Docker configuration and live native model services.

| Environment | Frontend / API | Database revision | Final state |
| --- | --- | --- | --- |
| Main | localhost:3000 / localhost:8000 | 20261104_0008 | Existing six services healthy; unchanged images/config/data |
| Existing preview | localhost:3001 / localhost:8001 | 20261104_0008 | App, DB, Redis and Mailpit remain stopped as initially found; speech worker healthy |
| Isolated M08 | 127.0.0.1:3008 / 127.0.0.1:8008 | 20261104_0009 | Native local demo; separate database and cookies; worker 8098 |

Main and preview each retain ten canonical A1 drafts, zero published lessons and
50 multiple-choice exercises. The demo additionally contains the explicitly
labelled six-format development fixture, version 0.1.1, pending review. No new
content was generated or published in 08.2. Canonical content remains 1.0.2.

## UX, grammar and exercise changes

New full-lesson snapshots use Introduction → Explanation → Examples → Exercises
→ Results. One reading task or exercise is shown at a time, with Back, Continue,
Exit, actual progress and a collapsible reference. Reading position uses the
existing session column; it survives refresh/exit without grading an answer.
Older immutable snapshots keep their original direct-exercise behavior. Focused
practice opens exercises directly.

Learn tabs retain valid CEFR URL context; returning from a lesson identifies the
related lesson. Browsing another level does not change the saved preference.
Grammar has one topic selector and authored explanation, use, translated French
examples, mistake notes, recap and practice count. The enriched être fixture has
three explicitly linked grammar exercises. Existing topics without authored
mistake notes or explicit practice mappings state that limitation honestly;
missing teaching material was not invented.

The existing accessible radio, blank, tile, matching, listening and written
controls remain server graded. Keyboard tile removal/reset and audio replay are
preserved. Feedback and history now display the learner's saved answer as well
as the explanation. A pending exact payload/idempotency key prevents duplicate
submission. An ambiguous save disables editing until retry or **Reload saved
progress**; the server determines whether the answer was recorded.

Results show real attempts, correct counts and completion state, plus Continue
learning and available mistake review. Focused practice does not increment full
lesson completion. No time, streak, weakness or acoustic score is invented.

## Genuine mistake review and empty states

Mistakes reuse M07's current, authorized unresolved exercise candidates and the
existing focused-session engine. Objective names are included only when backed
by the real objective mapping and frozen lesson snapshot; unmapped errors remain
lesson-level review. Correct later attempts remove resolved errors from current
recommendations, while original wrong grades remain in historical results.
Generic lesson answers neither create vocabulary review events nor change the
spaced-repetition schedule. Retirement and live permissions are rechecked.

Empty levels offer the existing AI Tutor and speaking pages. Due vocabulary is
suggested only when the authenticated API actually reports due items. Ordinary
learners still receive no draft content or draft-derived recommendations. The
authorized draft-preview banner remains backend controlled.

Additive API routes (all below `/api/v1`):

- `POST /learning/sessions/{id}/position`: strict integer 0–3, owned active guided
  full sessions only; existing auth/CSRF protections.
- `GET /learning/sessions/{id}/review`: owned, currently permitted evidence.
- `GET /learning/mistakes?level=A1&lesson_id=…`: current authorized mistakes.

No new migration, progress table, scheduler, answer-key exposure or identity
storage was introduced in 08.2. The existing 0009 migration remains isolated.

## Verification results

| Check | Actual result |
| --- | --- |
| Complete backend suite, speech environment | 251 passed, 2 existing dependency deprecation warnings; PostgreSQL scenarios enabled |
| Final navigation/evidence/cross-owner backend regressions | 4 passed after final assertions |
| Existing learning/interactive/preview focused backend checks | 24 passed |
| Frontend lint and typecheck | Passed |
| Next production build | Passed, 36 routes |
| Real M08 learning/preview browser suites | 7 passed; all six formats, keys hidden, keyboard/tile controls, listening, persisted results, mistake resolution and learner denial |
| Auth, AI, journey and compatibility browser group | 14 passed; includes three new journey cases and real registration/verification/resend |
| Genuine local model browser suite | 2 passed: Chromium WebM/Opus → Base ASR → Ollama → Piper/history; genuine short-name uncertainty → explicit correction/confirmation |
| Legacy API/redesign fixture checks | 2 passed; includes responsive widths 320–1440 |
| Legacy speech UI fixture checks | All 8 passed in bounded batches; separate fake inference from genuine model checks above |
| M07 daily study suite | All 3 passed across isolated runs: plan/review/lesson persistence, learner restrictions, simulated network outage |
| A1 curriculum and M04 live suites | 2 passed; ten packets, revised exercise, persistence/idempotency and learner denial |
| Content validation/audit | Valid: 10 drafts, 83 vocabulary entries, 50 exercises, 0 published, 0 rejected; six-format pack valid; technical integrity passed, publication NOT approved |
| Docker | Both Compose configurations validate; six existing main services and preview speech worker healthy; preview app intentionally remains stopped |
| Security | Publishable source scanned for active local credential matches and nested Git metadata; no findings; Gitleaks exit 0; private dumps/audio/models ignored |

The browser matrix covers 38 distinct cases using their required separate
fixtures, rather than a default run that skips environment-gated cases. Repeat
study runs initially failed on already-used accounts, then exhausted the test
API's real login limit. Fresh synthetic accounts and a restarted isolated API
namespace resolved the fixture state; limits were not relaxed. One focused
backend invocation initially inherited the demo CORS origin; rerunning with the
normal test configuration passed. These setup failures are not hidden.

The fast legacy speech batch also reached its existing 12-request/minute limit;
its remaining four cases passed after restarting only the guarded fixture.
No production rate limits were changed. Two genuine-model cases were skipped by
that legacy-only invocation and passed separately against the actual worker.

Voice tests used actual installed Base CPU/int8, `llama3.2:3b` and
`fr_FR-siwis-medium`, with synthetic French supplied through Chromium's capture
device. A genuine short utterance remained uncertain, editable and separately
persisted from corrected text. This does not verify the user's physical
microphone, subjective audio quality or pronunciation accuracy. The legacy
speech fixture intentionally uses fake inference to test error/cleanup paths.

No independent human browser evaluation was performed. Automated Chromium
interaction is the browser evidence. The manual acceptance path below remains
available for the user's own microphone and listening assessment.

## Authentication and permission evidence

Normal registration, login denial before verification, resend via the UI,
actual Mailpit verification link, onboarding, login/logout and persisted sessions
were exercised. Existing auth/backend tests cover expired/revoked sessions,
CSRF and rate limits. Real browser/backend checks cover ordinary learner draft
denial, protected routes, cross-owner session/position/review access, retirement
and production preview disabling. No ordinary account was promoted. The demo
reuses its existing active, verified synthetic admin; credentials are not printed.

## Database preservation and recovery

Before/after aggregate row fingerprints match for all **59 tables** in main and
all **59 tables** in preview, including user/session/profile/progress/conversation/
speech history and revision rows. Both original revisions remain 0008. All
**61 pre-existing demo session-exercise snapshots** match their original hash;
new test sessions append records normally. Preview DB alone was temporarily
started for these checks and restored to its initial stopped state.

`backend/scripts/verify_learning_recovery.py` performed actual consistent
`pg_dump` exports, restored each to a newly named disposable recovery database,
and applied exactly 0009 there. All **58 application tables**, using the original
columns, matched after migration; only the revision changed. Both temporary
recovery databases were removed. Private archives (346192 and 315929 bytes) are
ignored and protected by restricted Windows ACLs with no broad group grants.
Private baseline, recovery, content and security evidence lives under
`.publication-private/m08_2/`; no row values or connection secrets are reported.

The DB recovery drill does not back up external audio bytes, configuration or
model files. Existing volumes are untouched; respect speech retention settings.
Approved integration requires fresh backups plus protected configuration and
any required retained audio-volume backup, with a tested recovery procedure.

## Manual browser retest

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_m08_preview.ps1
# Paste the copied email into http://127.0.0.1:3008/login:
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py copy-email
# Paste the copied password, then sign in:
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py copy-password
Set-Clipboard -Value ''
```

Use the exact 127.0.0.1 URL; the dedicated M08 cookies isolate other environments.
Do not rerun database setup, promote a learner or use main credentials.

1. Open Learn; confirm **Authorized draft preview**. Select the six-format être
   development lesson. Read Introduction, Explanation and Examples using Back
   and Continue. Refresh midway, Exit, then resume the same saved reading stage.
2. Start exercises. Use the keyboard for choices, blanks, tile select/remove/
   reset and matching. Play/replay the listening sample; enter a written answer.
   Verify saved answer and explanation after each response. Exit/refresh midway
   and resume; repeated submission must not add an attempt twice.
3. Finish. Check the actual totals and saved answers. Deliberately wrong answers
   should offer Review mistakes. Complete its focused practice, return to the
   original results, and confirm the original wrong grade remains historical.
   Continue learning returns to the level/lesson context; dashboard full-lesson
   completion must not increase from focused practice.
4. Open Grammar, choose être, inspect all authored sections and start its real
   practice. Choose an empty level and verify honest alternatives without changing
   your profile level. Ordinary learners must retain the published-only empty state.
5. From a lesson, open AI Tutor and speaking. Allow microphone access, record
   French, stop, replay and send. For uncertain recognition, edit and explicitly
   confirm before submission. Check original/corrected text, tutor replay and
   session history after refresh. Assess your physical mic and audible output.
6. Sign out/in and verify persisted progress. For a new isolated account use the
   normal verification email flow; an unverified account must not enter the app.

## Local integration readiness — future approval required

Migration/recovery compatibility passed on disposable restores. This is technical
readiness evidence, not approval to deploy. Main/preview images still run their
old implementation. Preview-first integration needs an explicitly approved
maintenance window, fresh backup, configuration/audio-volume recovery decisions,
and a final source review. No commands below were executed as integration.

**Future approved preview maintenance only**, after safeguarding retained external
data and private configuration:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
$taskDocker = 'C:\Users\Shyam\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml config --quiet
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml stop preview-frontend preview-backend
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml up -d preview-db preview-redis preview-mailpit
.\.venv312\Scripts\python.exe backend\scripts\verify_learning_recovery.py --environment preview
if ($LASTEXITCODE -ne 0) { throw 'Backup/restore drill failed; stop integration.' }
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml build preview-backend preview-frontend
if ($LASTEXITCODE -ne 0) { throw 'Build failed; stop integration.' }
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml run --rm --no-deps preview-backend alembic upgrade 20261104_0009
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; stop integration.' }
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml up -d --no-build preview-backend preview-frontend
& $taskDocker compose -p fluentloop-preview -f docker-compose.preview.yml ps
Invoke-RestMethod 'http://localhost:8001/api/v1/health/ready'
```

The preview's existing startup command also runs the idempotent canonical draft
import. It does not install/publish the isolated six-format fixture. Preserve its
existing preview-only cookie names and trusted development flag. Verify normal
learners still cannot see drafts; only existing authorized accounts may preview.
Recheck main fingerprints and test preview end to end before considering main.

**Only after separate main-integration approval**, repeat protected external-data
backup and use these main commands:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
$taskDocker = 'C:\Users\Shyam\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
& $taskDocker compose config --quiet
& $taskDocker compose stop frontend backend
.\.venv312\Scripts\python.exe backend\scripts\verify_learning_recovery.py --environment main
if ($LASTEXITCODE -ne 0) { throw 'Backup/restore drill failed; stop integration.' }
& $taskDocker compose build backend frontend
if ($LASTEXITCODE -ne 0) { throw 'Build failed; stop integration.' }
& $taskDocker compose run --rm --no-deps backend alembic upgrade 20261104_0009
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; stop integration.' }
& $taskDocker compose up -d --no-build backend frontend
& $taskDocker compose ps
Invoke-RestMethod 'http://localhost:8000/api/v1/health/ready'
```

These snippets stop on explicit migration/build/drill failures. An operator must
also stop on any Compose configuration/start/health failure. Current backend
startup upgrades `head`; before future execution verify that head is still
0009 and review any additional migrations. Keep main draft preview disabled.
The drill intentionally refuses a source already beyond 0008; do not run its
pre-integration procedure blindly after migration.

For recovery, stop app writers and retain the new-data database. Restore the
verified private archive into a **new** recovery database, validate fingerprints,
and switch only the approved environment's private database URL/images during
maintenance. Do not overwrite the original database or automatically downgrade
after interactive records exist; 0009's downgrade guard intentionally refuses
lossy reversal. Exact recovery target names/connection changes require the
operator's current backup selection and approval; no destructive in-place
restore command is prescribed.

## Files and remaining work

08.2 backend changes: learning schemas/routes and the learning/interactive
services; new `test_learning_experience.py` and `verify_learning_recovery.py`.
Frontend changes: courses/grammar/practice/lesson/session/results pages;
grammar details, lesson library/tabs, new lesson reading, alternatives and mistake
practice components; learning/context utilities and journey/auth/compatibility
browser tests. See the architecture guide for route and snapshot details.

Remaining work is independent curriculum review/publication approval, authored
notes/exercise links for incomplete reference topics, the user's physical-mic
and listening assessment, and separately approved environment integration.
ASR may still mishear names/short speech; no validated acoustic pronunciation
score exists. No feature or role bypass is proposed to work around these limits.
