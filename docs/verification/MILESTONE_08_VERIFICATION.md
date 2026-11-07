# Milestone 08 local verification

Historical verification from November 4. For the current authorized login,
cookie isolation and fixture revision 0.1.1, use [Milestone 08.1 manual testing](MILESTONE_08_1_MANUAL_TESTING.md).

Date: 2026-11-04, Europe/Paris. **Implemented and verified locally.**
Branch remains `feature/a1-curriculum-review`; HEAD remains
`76b3e3f2577dd9cac621207358a9b9a4f1f3fb84`. All M08 changes are uncommitted.
Nothing was staged, committed, pushed, merged, deployed or published. No remote
or existing pull request was changed. Milestone 09 was not started.

## Implemented behavior

- Five primary destinations remain Home, Learn, AI Tutor, Speak and Profile.
  Learn contains Lessons, Grammar and Practice tabs in the existing minimal
  white/purple design, including 320-pixel layouts.
- Lesson cards show real units/objectives, duration, saved progress and
  Start/Continue links. Existing course, lesson, session and result URLs work.
- Grammar includes English explanations, French examples/translations, usage,
  common mistakes, related vocabulary, recap, objective/source/version notes
  and pending review status for the small enriched draft.
- Six formats work through the existing persisted server engine: multiple
  choice, fill blank, stable-ID sentence order, stable-ID matching, listening
  with existing French Piper, and deterministic short written responses.
- Immediate feedback, Unicode normalization with significant accents, saved
  answers, resume, immutable keys, owner checks, transactional idempotency and
  completion conditions remain server-authoritative.
- Focused grammar/sentence/listening/mistake practice saves attempts without
  completing full lessons. Vocabulary uses existing `/review`, not a second
  scheduler. Generic practice does not duplicate review-card scheduling.
- M07 can recommend objective-linked mistake practice using actual unresolved
  attempts. Legacy unmapped errors remain lesson-level recommendations.
- Lesson/grammar actions reuse existing owned, authorized, CEFR-aware tutor
  and speaking conversations. Core lessons need neither Ollama nor ASR.
- Draft/topic permission changes are checked on start, read, resume, answer,
  completion, listings, practice, daily activity and listening access.

See [architecture](../architecture/interactive-learning-engine.md),
[grammar/practice](../learning/grammar-practice.md),
[exercise formats](../learning/exercise-formats.md) and
[security](../security/exercise-grading-and-content-permissions.md) for schemas,
API contracts and implementation details.

## Verification results

| Check | Actual result |
| --- | --- |
| Complete backend suite with PostgreSQL and native audio dependencies enabled | **239 passed**, 0 failed/skipped; two existing dependency deprecation warnings; 243.22 seconds |
| Final focused learning/study/API and PostgreSQL suite after security review additions | **60 passed**, 0 failed; two existing warnings |
| Explicit PostgreSQL scenarios | 7 passed within the complete suite: AI, speech, two M07, two M08 and A1 correction preservation |
| M08 regression cases | 14 functional/API/normalization cases plus 2 real PostgreSQL cases |
| Canonical source validation | 10 draft lessons, 83 vocabulary occurrences, 50 exercises, 5 planned higher-level courses, 0 rejected/published |
| Canonical read-only database audit in isolated M08 DB | Technical integrity passed for all 10 original lessons; publication approval false |
| Interactive source validation | 6 formats, draft, pending independent review |
| Interactive PostgreSQL reimport | Second import: 0 inserted, 0 updated, 45 unchanged, 0 deleted |
| ESLint | Passed |
| TypeScript (`next typegen` and `tsc --noEmit`) | Passed |
| Production build | Passed; 36 generated pages/routes |
| Playwright | **29 unique tests passed across separate fixture batches**, 0 remaining failures |
| Final M08 browser rerun | 4 passed, using real local API/PostgreSQL and Piper listening audio |
| Existing Docker main/preview | 12/12 services healthy; no rebuild/restart/deployment |
| Main/preview data comparison | 59/59 aggregate table fingerprints unchanged in each database |
| Main/preview schema and publication state | Both remain 0008, 10 draft lessons, 0 published |
| Active local credential comparison | No matches in publishable files |
| Git history secret scan | No leaks in five existing commits; history unchanged |
| Final path-aware working-tree scan | Gitleaks clear across 278 publishable text files; no new scanner allowlist added |
| Whitespace/diff checks | Passed; no staged changes |

The populated rollback fixture also checks existing users, auth sessions, saved
lesson answers/progress, AI messages and uncertain speech history. An empty
multiple-choice payload uses SQL NULL; the downgrade guard also treats legacy
JSON null as empty while continuing to reject genuine structured answer loss.

PostgreSQL tests used newly created explicitly named test databases. They
exercise fresh installation, populated 0008 → 0009 upgrade, empty rollback,
lossy rollback refusal, row preservation, real concurrent duplicate submissions,
historical key changes, recommendations and permissions. No real learner records
were used as test fixtures.

Browser totals are deliberately not presented as one combined fixture run:

| Browser batch | Passed | Test boundary |
| --- | ---: | --- |
| Existing mocked auth/tutor/lesson UI | 10 | Browser with mocked API responses |
| New M08 | 4 | Actual API/PostgreSQL; real Piper listening; synthetic accounts |
| Existing AI API | 1 | Actual API/PostgreSQL; deterministic model provider |
| Existing voice | 8 | Actual API/PostgreSQL and Chromium MediaRecorder; fake microphone/inference fixtures |
| Responsive redesign | 1 | Actual isolated API; widths 320/390/900/1440 |
| Existing daily study | 3 | Actual API/PostgreSQL and existing scheduler; one intentionally simulated plan-network outage |
| Canonical A1 and M04 | 2 | Actual API/PostgreSQL; draft audit, grading, replay, completion and owner denial |

Initial browser runs exposed duplicate Learn navigation, 320-pixel tab overflow,
an ambiguous matching label and a missing legacy radio `value`. These were
corrected and the relevant browser suites passed afterward. Repeated fixture
logins/speech requests also hit the unchanged limits; fresh isolated fixture
batches were used rather than weakening rate limits. A test-fixture lesson-ID
mismatch and readiness/Windows console issues were corrected in the local
verification helper. These are not omitted passing tests or disabled safeguards.

## Actual model inference

These checks used installed models, not fake providers:

- Faster-Whisper **Base**, CPU/int8, recognized a 5.19-second French Piper sample:
  “Bonjour, je m'appelle Camille, j'habite à Paris, je voudrais une baguette s'il
  vous plaît.”
- Public attributed `fr-bonjour.ogg`: 1.2 seconds, `transcribed`, “bonjour”.
- Public attributed `en-us-hello.ogg`: 0.488 seconds, `non_french`, empty accepted
  transcript. Silence safeguards also remain covered by the backend suite.
- Existing French Piper voice `fr_FR-siwis-medium`: 22,050 Hz WAV, 228,908 bytes
  for the longer synthetic sample.
- Ollama `llama3.2:3b` was available and generated through both the provider and
  the authenticated existing tutor with authorized draft sources.
- Full authenticated voice pipeline: synthetic Piper French input → Base ASR
  → Ollama tutor → Piper reply. Result `success`, `transcribed`, tutor present,
  tutor audio `ready`; authenticated WAV retrieval returned HTTP 200 and
  **44,588 bytes**. This was synthetic speech, not a claim of testing the user's
  physical microphone or accent. Browser microphone lifecycle tests use
  Chromium's fake device.

Local raw model/report artifacts and synthetic browser expectations remain in
ignored private directories. They contain no production publication artifact.

## Database and curriculum preservation

Migration **20261104_0009**, after verified head 0008, is additive and is applied
only to isolated M08 and test databases. It adds private structured exercise
metadata, objective/topic references, explicit grammar publication/teaching
fields, structured attempts and focused-session identity. It retains existing
IDs/answer strings and extends the existing active-session index. A fresh-install
compatibility check handles revision 0003's live ORM table creation. No old
migration was rewritten. Downgrade refuses to discard used M08 data.

The original A1 `course.json` and its 50 answer keys remain unchanged. The small
new source is separate: one draft module, six exercises, version 0.1.0, tied to
existing être grammar/objective/vocabulary identities. It adds no approvals.
The local M08 demonstration therefore has an additional draft implementation
lesson; the main and preview databases retain exactly their original ten drafts.

The baseline/final comparison covers all 59 existing tables in each application
database, including users, authentication sessions, lesson progress/attempts,
curriculum, AI memory, speech history, vocabulary review and daily plans. No
fingerprint changed. Both Alembic revisions remain `20261104_0008`.

## Local URLs

| Purpose | URL |
| --- | --- |
| M08 frontend | http://127.0.0.1:3008 |
| Lessons / Grammar / Practice | http://127.0.0.1:3008/courses · http://127.0.0.1:3008/grammar · http://127.0.0.1:3008/practice |
| M08 API documentation | http://127.0.0.1:8008/docs |
| M08 API readiness | http://127.0.0.1:8008/api/v1/health/ready |
| M08 speech worker | http://127.0.0.1:8098/health (existing worker authentication required) |
| Existing main | http://localhost:3000 / http://localhost:8000/api/v1/health/ready |
| Existing preview | http://localhost:3001 / http://localhost:8001/api/v1/health/ready |
| Existing Ollama | http://127.0.0.1:11434 |

M08 native services bind loopback only. Ports 8018/8019 and frontend 3011 were
temporary regression fixtures; they are not the M08 demo or a deployment.

## PowerShell verification

Use separate terminals for long-running local services. Existing Docker
PostgreSQL/Redis and configured Ollama/models must already be available. The
helper reads private root configuration without printing connection strings.
Do not run a generic database upgrade against the main or preview DB.

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
# First setup only; already performed in this verification.
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py setup
# Separate terminals, only if the corresponding local service is not running:
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py api
.\.venv-speech\Scripts\python.exe backend\scripts\m08_local.py worker
```

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI\frontend'
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8008/api/v1'
npm.cmd run dev -- --hostname 127.0.0.1 --port 3008
```

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py tests
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py preservation
Set-Location frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3008'
$env:PLAYWRIGHT_API_BASE_URL='http://127.0.0.1:8008/api/v1'
$env:M08_E2E_REAL_API='1'
npx.cmd playwright test interactive-learning.spec.ts --workers=1
```

For original opt-in suites, use fresh guarded `m08_local.py legacy-speech` and
`legacy-study` APIs in separate runs, point the single local Next dev server at
8018 or 8019 on frontend port 3011, and wait for API startup before testing.
Use `SPEECH_E2E_REAL_API=1`/`AI_E2E_REAL_API=1` for speech/AI/redesign, or
`STUDY_E2E_REAL_API=1` for `study.spec.ts`. Run `m08_local.py curriculum-browsers`
with the study fixture for A1/M04. `study-accounts` prepares fresh synthetic
study accounts when repeating a partially completed study test. Do not run
different Playwright commands concurrently in the same output directory. Keep
unchanged rate limits; restart only test fixtures between independent batches
when needed. Restore frontend API 8008/port 3008 afterward.

## Manual browser check of every format

1. Open the M08 frontend. Use the synthetic admin email in ignored
   `.speech-data/m08-browser-fixture.json` and the isolated browser password
   defined in `backend/scripts/m08_local.py`. Do not use a main/preview learner
   account. The helper has already completed onboarding at A1.
2. Open Learn. Check Lessons, Grammar and Practice, then the enriched être
   grammar explanation. Read usage, examples/translations, common mistakes and
   recap; inspect version/review notes and related vocabulary.
3. In Lessons, open **Être: understand, practice and remember**. The Draft Preview
   label must be visible. Start/continue, or retake if the test already completed
   it. Read the introduction and explanation before answering.
4. Multiple choice: select **suis** and submit. Check saved server feedback.
5. Fill blank: enter **es** for `Tu ___ ici.`; submit and continue. Save and exit,
   then use Continue in the lesson library to verify restored feedback/progress.
6. Sentence building: choose **Je**, **suis**, **étudiant**. Try removing a word,
   Undo and Reset before submitting. Repeat using Tab/Enter on a narrow viewport.
7. Matching: map `Je suis ici.` → `I am here.`, `Tu es ici.` → `You are here.`,
   `Elle est ici.` → `She is here.`. Selects require distinct right-hand choices.
8. Listening: Load French audio, play and replay using native controls, then
   select **She is here.**. If the worker is unavailable, the UI must offer a
   retry rather than fabricate audio or a grade.
9. Written response: enter **Je suis étudiante.** (or the masculine authored
   variant). Submit and finish. Refresh the results and verify saved feedback.
   On a separate retake, an accentless `etudiant` must not be accepted as the
   accented authored form.
10. Open Practice → Sentence building or Grammar. Finish a focused session and
    verify it says practice complete; the full lesson completion count must
    not increase. Vocabulary must open existing Review. Mistake practice is
    available only after a real unresolved error, not an invented weakness.
11. Open Ask AI Tutor or Practice speaking from an authorized A1 lesson. Check
    existing conversation routes/history. For actual microphone testing, allow
    the browser microphone, record French, listen before submission, edit an
    uncertain transcript and explicitly confirm it before sending. Original
    recognition must remain distinct from the corrected utterance in history.
12. Sign in as the separate synthetic ordinary learner. Draft lessons, grammar,
    practice exercises, listening and lesson-linked AI/speech actions must be
    unavailable. Saved sessions from the admin must not be accessible.
13. Check Home's daily plan and Profile's saved level. Changing level must keep
    earlier learning history. Check exactly five primary navigation destinations
    and no horizontal overflow at 320/390 pixels.

## Remaining limits

- All ten canonical A1 lessons and the new six-exercise module remain draft.
  Independent French-language, pedagogy, answer-key and rights reviews are
  pending. Automated tests are not publication approval or a license grant.
- Only the small A1 module supplies all six new formats. Higher CEFR content is
  not fabricated; empty authorized categories/levels are intentional.
- Written grading accepts explicit variants only, preserving accents. It does
  not assess open-ended subjective writing or infer unlisted valid answers.
- Base ASR can still mishear names, accents, short phrases or noisy microphones.
  Recognized/edited text remains reviewable. No validated acoustic pronunciation
  score is available or claimed.
- Ollama output can contain factual, register or personalization errors. Live
  inference confirms connectivity and bounded authorized context, not independent
  pedagogical accuracy. It never overrides exercise grading.
- New local/test databases are retained for inspection; no shared PostgreSQL
  volume was reset. M08 changes are not applied to the existing Docker apps.

## Changed files

Backend model/schema/route changes: `app/curriculum_models.py`,
`app/learning_models.py`, `app/learning_schemas.py`, `app/study_schemas.py`,
`app/api/v1/learning.py`, `app/api/v1/curriculum.py`, `app/ai/retrieval.py`,
`app/services/learning_service.py`, `app/services/grading_service.py`,
`app/services/daily_learning_service.py` (all under `backend/`).

New backend files: migration 0009, `app/interactive_content.py`,
`app/services/exercise_formats.py`, `app/services/content_permissions.py`,
`app/services/interactive_learning.py`, `content/practice/etre-interactive.json`,
`scripts/m08_local.py`, `tests/test_interactive_learning.py`,
`tests/test_interactive_postgres.py`. Compatibility test helpers changed:
`scripts/prepare_study_browser.py`, `tests/test_study_postgres.py`.

Frontend changes: `app/courses/page.tsx`, `app/grammar/page.tsx`,
`app/learn/[lessonId]/page.tsx`, `app/learning/sessions/[sessionId]/page.tsx`,
`app/learning/results/[sessionId]/page.tsx`, `components/app-shell.tsx`,
`lib/api.ts`, `lib/learning.ts` (all under `frontend/`).
New: `app/practice/page.tsx`, `components/learning-tabs.tsx`,
`components/lesson-library.tsx`, `components/grammar-details.tsx`,
`components/lesson-actions.tsx`, `components/exercise-input.tsx`,
`e2e/interactive-learning.spec.ts`.

Documentation: README and the five requested M08 architecture/learning/security/
verification guides. Private env files, databases, recordings, generated audio,
model weights, caches and test reports remain ignored and unstaged.
