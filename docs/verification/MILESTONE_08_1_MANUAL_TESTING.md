# Milestone 08.1 — authorized local manual testing

For current Chrome sign-in and account checks, see
[M08 developer-preview authentication](M08_PREVIEW_AUTH_CORRECTION.md).

For the subsequent guided lesson flow, current verification and integration
readiness, see [Milestone 08.2](MILESTONE_08_2_LEARNING_EXPERIENCE.md). The access
helper below remains valid; the results recorded here describe 08.1.

Verified on **2026-11-05 (Europe/Paris)**. Local implementation only. No commit,
push, pull request, merge, deployment, publication, volume reset, production
credential change or Milestone 09 work was performed.

## Findings and environment architecture

The empty states are correct for ordinary learners. The six-format content and
an already authorized, email-verified synthetic admin existed in a separate M08
database. They were not missing from the project, and the main learner account
must not be promoted to reach them. At inspection the native M08 services and
the old preview application were stopped. A browser session's particular account
cannot be inferred from an empty-state label alone; the new backend-controlled
access banner makes its actual scope visible.

| Environment | Actual routing and database | Schema/content | Initial state |
| --- | --- | --- | --- |
| Main, `localhost:3000` | Frontend → `localhost:8000/api/v1`; Docker `db:5432`, host 5432, database `fluentloop` | `20261104_0008`; canonical A1 1.0.2; 10 drafts, 50 MC exercises, no M08 fixture | Six main Docker services healthy; preview flag false; no admin accounts |
| Old preview, `localhost:3001` | Frontend → `localhost:8001/api/v1`; Docker `preview-db:5432`, host 5433, database `fluentloop_preview` | `20261104_0008`; canonical A1 1.0.2; 10 drafts, 50 MC exercises, no M08 fixture | Frontend/backend/DB/Redis/Mailpit stopped; speech worker healthy; trusted dev preview flag true; one existing verified admin |
| M08, `127.0.0.1:3008` | Native Next → `127.0.0.1:8008/api/v1`; PostgreSQL host 5432, database `fluentloop_m08_local_*`; Redis database 14; native speech worker 8098; Ollama 11434 | `20261104_0009`; canonical A1 1.0.2 plus one six-format draft fixture, now 0.1.1 | Native services stopped; dev preview already enabled; designated synthetic admin active/verified/A1; designated synthetic learner still a learner |

Both Docker frontend route manifests lacked `/practice`; neither installed
Docker frontend had the new M08 interface. They were not rebuilt. The preview
database alone was temporarily started for read-only inspection and restored to
its original stopped state afterward. Its application was not started or changed.
The main application remained running and unchanged.

### Authentication isolation

Main uses `fluentloop_session` / `fluentloop_csrf`; old preview uses
`fluentloop_preview_session` / `fluentloop_preview_csrf`. M08 previously relied
on default cookie names. It now uses **`fluentloop_m08_session` /
`fluentloop_m08_csrf`**, configured only in its private local environment and its
frontend startup process. Cookies are scoped by hostname, not port; use the exact
`127.0.0.1:3008` URL and these dedicated names. No main/preview sessions were
revoked, credentials rotated or normal learner roles changed.

`GET /api/v1/learning/access` reports the authenticated account's effective scope:
`draft_preview` or `published_only`, plus its saved level. It exposes no keys,
tokens or database configuration. Preview still requires an active verified
admin, the trusted backend flag, and `APP_ENV=development`. Production disables
preview even if someone sets the flag. No query parameter/client switch grants it.

## Start and sign in without printing credentials

Prerequisites: existing Docker main PostgreSQL/Redis/Mailpit, installed Node and
Python environments, existing Base/Piper model files and configured local
Ollama. The M08 environment is prepared already; **do not rerun the original
database-creating setup or reset any database**.

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_m08_preview.ps1
```

The launcher validates/reuses the existing synthetic verified admin, idempotently
prepares only the existing isolated fixture, starts native API/worker/frontend
hidden on loopback, and waits for readiness. It does not build/start Docker
stacks, migrate application databases, create accounts or grant permissions.
Other processes occupying these ports are refused rather than terminated.
Both reuse and a fresh three-service start were tested. Protected runtime logs
are under ignored `.publication-private/m08_1/runtime/`.

1. Open **http://127.0.0.1:3008/login**. Sign out first if the page is currently
   using the separate synthetic learner. Do not use a main/preview user account.
2. Copy the *existing isolated admin email* to the local clipboard, then paste
   it into Email:

   ```powershell
   .\.venv312\Scripts\python.exe backend\scripts\m08_local.py copy-email
   ```

3. Copy its existing synthetic password, then paste into Password:

   ```powershell
   .\.venv312\Scripts\python.exe backend\scripts\m08_local.py copy-password
   ```

4. Clear the clipboard after pasting and click Sign in:

   ```powershell
   Set-Clipboard -Value ''
   ```

The copy helpers never print either value. They refuse other databases,
non-synthetic accounts, unverified/inactive users or a missing existing admin
role. Password copying validates the existing hash; it never resets it. If the
fixture password was changed, use the normal email password-reset flow. Email
verification, actual login, CSRF and rate limits remain mandatory.

Open Learn and confirm **“Authorized draft preview”** before testing. If it says
“Published content only,” use the profile and access checks in the current
Chrome guide above to identify the active account and its effective scope.
Access to drafts is deliberately denied to ordinary accounts.

## Fixture and grammar revision

`backend/content/practice/etre-interactive.json` is now **0.1.1**, explicitly a
development fixture. It reuses the existing stable source exercise IDs, être
topic, learning objective and vocabulary identities. A fourth *incorrect*
multiple-choice option was appended; the original correct index remains 1.
The canonical ten A1 packets, 150 options and answer indices were not changed.
No new schema migration was needed; 0009 was already installed only in M08.

The normalized 0.1.0 source is preserved in
`backend/content/practice/archive/etre-interactive-0.1.0.json`; its original import
digest was verified before archiving. It is historical evidence, not the current
import target. All **37 pre-existing 0.1.0 session-exercise snapshots retain
their exact aggregate fingerprint**. Old sessions keep their original options
and keys; complete an older session, then retake to test the current four-option
version rather than altering history.

The enriched A1 être grammar includes English explanation, when to use it,
`je suis / tu es / elle est`, bilingual examples, common mistakes, related
vocabulary/exercises and a recap. It links to real authorized practice and the
existing tutor/speaking actions. Source/license and independent review remain
pending. Developer fixtures are not independently approved public lessons.

### Manual test of all six formats

In Lessons, open **Être: understand, practice and remember**, read its
development-only introduction and begin/retake the full lesson. Current version
is 0.1.1. Keep the Draft Preview label visible.

| Format | Manual action | Verified behavior |
| --- | --- | --- |
| Multiple choice | Four options: es / suis / est / sommes. Choose **suis**, or intentionally choose **es** to test a mistake. | Owned server submission; correct/incorrect feedback and saved attempt; original key index unchanged |
| Fill blank | `Tu ___ ici.` → **es**. | Whitespace normalization; explanation; significant accents remain protected by deterministic tests |
| Sentence order | Select **Je → suis → étudiant**. Try remove, Undo and Reset first. | Shuffled stable IDs, keyboard/mobile controls, exact server order grading |
| Matching | `Je suis ici.` → `I am here.`; `Tu es ici.` → `You are here.`; `Elle est ici.` → `She is here.` | Distinct complete matching set; saved server feedback shows mappings only after submission |
| Listening | Load/play/replay French audio; choose **She is here.** | Actual existing Piper; authenticated bounded WAV; no script/key in initial API JSON; unavailable audio offers retry |
| Written | Translate “I am a student.” → **Je suis étudiant.** or **Je suis étudiante.** | Explicit authored variants, accents preserved, submitted text retained in PostgreSQL |

Every step uses the existing session/attempt engine. Source keys, accepted
orders/variants, mappings and listening scripts remain hidden before submission.
The words taught in lesson notes remain readable; that is not a public key API.
First audio preparation can take longer on a cold worker; browser checks wait
within the existing speech timeout rather than weakening service validation.

Exit after two answers, refresh and Continue. Finish, refresh results, sign out
and sign in again. The automated mixed run saved **5 correct / 1 incorrect,
83.33%**, resumed **2 / 6** midway and retained the submitted written sentence
after sign-in. Identical answer retries were idempotent. No real learner history
was used or overwritten.

## Practice availability and Milestone 07

Practice availability comes from actual authorized backend candidates. The
catalog now supplies an explicit reason: available, no published content, no
permitted content, or no unresolved mistakes. Counts are not fabricated.
Unavailable Start practice buttons have a native disabled attribute, grey
background/text, a `not-allowed` cursor and an accessible explanation. Checking,
empty and failed availability cannot start an empty session. The backend still
rechecks authorization and rejects empty practice with 409.

- Authorized initial fixture: grammar 3, sentence building 1, listening 1.
- Mistake count depends on genuine unresolved attempts. Zero mistakes is valid;
  the mixed browser test created an actual recorded wrong answer as evidence.
- Vocabulary opens existing `/review`. Generic exercise completion did not
  increase review-attempt totals or schedule cards twice.
- The real demo daily-plan creation/read/refresh/sign-in flow retains the plan
  identity and saved A1 level. Existing SRS scheduling, enrolled-item grading,
  due dates and concurrency are covered by the real PostgreSQL suite.
- Focused sessions still do not complete a full lesson. Existing objective
  recommendations use current-version owned evidence; old unmapped snapshots
  never acquire invented weaknesses from later source mappings.

## AI and speaking demonstration

From Grammar, use Ask AI Tutor. It opens the existing owned conversation with
authorized bounded lesson context and the saved CEFR level. Practice speaking
opens the existing voice conversation; it does not introduce a new pipeline.

For a physical microphone check, allow browser microphone access, Record French,
stop, replay and Send recording. Real automated browser verification instead
used **synthetic Piper French input through Chromium's microphone device**:
MediaRecorder WebM/Opus → actual Base ASR → actual Ollama → actual Piper reply.
Audio replay and stored conversation history passed. This does not claim the
user's physical microphone or accent was tested.

A separate real Base inference on a 697 ms synthetic “Camille” sample produced
`uncertain`, “Camille !”. The real API/browser retained that original, sent no
tutor message automatically, accepted an explicit edit to “Je m'appelle Camille.”,
and recorded `user_confirmed` with edited provenance after Confirm and send.
The original uncertain turn remained unchanged in persisted history. No ASR
threshold, language rejection or silence safeguard was disabled.

## Actual verification results

| Check | Result in this milestone |
| --- | --- |
| Complete backend with native audio dependencies and isolated PostgreSQL | **247 passed**, 0 failed/skipped; 2 existing dependency deprecation warnings; 277.85 s |
| New focused preview authorization tests | **8 passed**: auth/access/counts, configuration/role/verification matrix, production denial, revocation and immutable snapshot/key preservation |
| Real browser learning/availability suite | **7 passed** against M08 API/PostgreSQL, including actual Piper listening |
| Real browser speech suite | **2 passed**: recorded WebM/Opus + live inference/history, and genuine uncertain transcript edit/confirmation |
| Real-environment learning/speech browser cases | **9 passed**; actual environment, not mocked API/model responses |
| Additional existing auth/tutor/lesson browser regressions | **10 passed**: 9 mocked UI cases plus the actual registration → email verification → login → onboarding/profile flow in the isolated M08 DB |
| Total distinct browser cases run | **19 passed** across fixture batches; no remaining failures |
| Canonical content validation/audit | 10 drafts, 83 vocabulary occurrences, 50 exercises; technical integrity passed; no publication approval |
| Interactive fixture validation/reimport | Six formats, draft; repeated preparation: 0 inserted, 0 updated, 46 unchanged, 0 deleted |
| ESLint / TypeScript | Passed |
| Production build | Passed; 36 generated pages/routes. First sandboxed run could not fetch existing Google fonts; rerun with network access passed. No font/design workaround or deployment. |
| Main preservation | **59 table fingerprints including revision unchanged**; migration 0008, 10 drafts, 0 published |
| Preview preservation | **59 table fingerprints including revision unchanged**; migration 0008, 10 drafts, 0 published; original stopped container state restored |
| Historical M08 preservation | All 37 old 0.1.0 session-exercise snapshots unchanged |
| Native launcher | Existing-process reuse and fresh API/worker/frontend startup passed; loopback only |
| Source security scan | 284 publishable text files checked; no active credential matches; path-aware Gitleaks clear; no new allowlist |

The backend suite includes real PostgreSQL migration preservation, populated
accounts/auth/progress/AI/speech history, concurrency, ownership, review scheduling
and duplicate-answer checks. The new security cases also verify an ordinary or
unverified account cannot get preview, the trusted flag can revoke access, and
production remains published-only. Browser tests verify empty Grammar and grey
disabled practice buttons for the separate existing learner without promoting it.

The Docker baseline is not yesterday's all-running state: today six main
services plus the preview speech worker were healthy. The other five preview
containers were already stopped. No images were rebuilt, no main service was
restarted and no claim is made that the stopped preview application is healthy.
The preview DB was restored to stopped after read-only inspection. Main readiness
uses `http://localhost:8000/api/v1/health/ready`.

## PowerShell verification commands

Use the launcher above for the demo. Run checks from the existing workspace:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py tests
.\.venv312\Scripts\python.exe -m pytest backend\tests\test_authorized_preview.py -ra
Set-Location frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3008'
$env:PLAYWRIGHT_API_BASE_URL='http://127.0.0.1:8008/api/v1'
$env:PLAYWRIGHT_CSRF_COOKIE_NAME='fluentloop_m08_csrf'
$env:M08_E2E_REAL_API='1'
npx.cmd playwright test interactive-learning.spec.ts authorized-preview.spec.ts --workers=1
$env:M08_SPEECH_LIVE='1'
npx.cmd playwright test authorized-preview-speech.spec.ts --workers=1
```

Live speech tests require installed Ollama/Base/Piper and the already prepared,
ignored synthetic WAVs in `.speech-data/m08_1/`; if absent they skip and must not
be reported as passes. They are not personal recordings. Repeated sign-ins
consume the unchanged 10-per-15-minute login limit; honor Retry-After rather
than disabling it. Test traces, model outputs and runtime logs stay private and
ignored. Never dump `.env`, cookies, database URLs or clipboard credentials into
the terminal or a report.

## Limits and files changed in 08.1

All ten canonical A1 lessons and the separate development fixture remain draft.
Independent French/pedagogical/answer-key/licensing review is pending. Supporting
six CEFR preferences does not imply complete content at all levels. Empty higher
levels and empty mistake review are valid states.

Base can still confidently mishear short speech: “Tu es ici.” became “C'est ici.”
in an actual 708 ms sample. Longer French was recognized and short “Camille” was
honestly marked uncertain. ASR is not validated acoustic pronunciation scoring.
Ollama can still make teaching/personalization errors; it never overrides grading.

08.1 changes: backend learning access/catalog metadata and verified-active
preview eligibility; isolated local helper and `scripts/start_m08_preview.ps1`;
fixture 0.1.1 plus digest-verified 0.1.0 archive; LearningTabs access banner;
grey/disabled Practice UX; configurable Playwright CSRF cookie; preview/backend
and real speech browser regression tests; README/current-workflow links and this
guide. **No new migration, authentication bypass, learner-role change, password
reset, production credential change or publication action.** Earlier uncommitted
Milestone 08 source changes were preserved; branch and HEAD remain unchanged.
