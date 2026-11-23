# Personal local-only implementation verification

## Current checkpoint — 23 November 2026, authorized import and local acceptance

This section supersedes the historical checkpoint sections below. Personal use
only: no publication, deployment, commit, push, role elevation or M08 merge.

### Available personal curriculum

The owner confirmed the exact 80-lesson import directly in chat. A fresh consistent
custom-format backup of main was verified, restored into a disposable database,
and the exact 29 release packs rehearsed before the main transaction. All 150
new scored answer keys passed correct/wrong checks. Import and repeated reuse
were idempotent; prerequisites and foreign keys validated. All pre-existing rows
were preserved, including the previous 101 lessons and their versions/keys.

| Stage | Main lessons | Scored exercises | Educational status |
|---|---:|---:|---|
| A0 preparation | 12 | 44 | Introductory draft; not an official CEFR level |
| A1 | 39 | 172 | Unpublished, human review pending |
| A2 | 26 | 82 | Unpublished, human review pending |
| B1 | 26 | 82 | Unpublished, human review pending |
| B2 | 26 | 80 | Unpublished, human review pending |
| C1 | 26 | 80 | Unpublished, human review pending |
| C2 | 26 | 80 | Unpublished, human review pending |
| **Total** | **181** | **620** | **0 published** |

All 52 mapped modules have accessible draft input for the confirmed learner.
The confirmed account remains a learner, can preview only through the existing
UUID allowlist, and cannot author/publish. Ordinary learner denial is tested.
A0 is stored as introductory A1 preparation while displayed separately on the map.

There are 50 open writing/transfer task lessons with speaking/revision prompts;
these are not 50 independently rated speaking assessments. The assessment catalog
offers 225 per-lesson objective components and 50 writing components. These reuse
existing exercises, not 225 new exams. `/checkpoints` adds 52 module and seven
sampled level-end plans, with qualitative writing/speaking rubrics, no fabricated
aggregate proficiency score and no automatic level promotion. Components save
through the existing frozen, owned, idempotent assessment histories.

Five later unscored A0/A1 writing bridges passed disposable PostgreSQL import,
prerequisite, duplicate-prevention and prior-row preservation checks. They remain
absent from main and require separate import approval. A C2 model companion
(582-word essay, short panel and contributor note) is staged as a review file,
not an imported/served lesson. No future batch is authorized.

### Preservation and local runtime

Post-import main table signatures match across a controlled graceful stop and
normal restart, and after live tests. M08 still matches its historical baseline.
Main retains two users, eight AI conversations/16 messages, six speech sessions/
eight turns. Main full-lesson sessions/progress and writing submissions remain
zero as recorded before this work; no artificial owner learning was generated.
M08 retains 23 lessons/81 exercises, 35 learning sessions/four progress rows,
31 AI conversations/12 messages and 15 speech sessions/seven turns. These are
whole-database counts, not claims about a particular user's content.

Fresh before/after backups are ignored private artifacts under
`.publication-private/final-acceptance-20261123/`. Before: 552,003 bytes, SHA-256
`2f70f7a8ec289f4a966157dd3041d394ed6224cd896d1313e8a4cb48c2896a55`.
After: 694,741 bytes, SHA-256
`5bdb7b60631b3db17f981aec8aee87df2822c7d98038eca6ecef39ca23b86a22`.
Both reverified against manifests. Older recovery copies were retained.

Normal startup uses only the approved existing PostgreSQL/Redis/Mailpit containers,
native API/frontend/speech worker and existing Ollama model. No personal Ubuntu
boot is required. Infrastructure-only maintenance mode is explicit, supervised,
and does not launch API/frontend/speech writers. Normal Start does not run Alembic
migrations or curriculum imports. The normal runtime was restarted successfully;
audit-only servers use separate synthetic databases. The owner console must remain
open during daily use. See the operation guide for exact commands.

### Verification evidence and remaining acceptance

- Real PostgreSQL/AI/speech suite: **34 passed**, including migrations only on
  guarded disposable databases, Ollama responses, transcription and Piper audio.
- Standard browser suite: **26 passed, 37 optional tests skipped**. Separately
  enabled historical admin fixture suite: **7 passed**. Personal live suite:
  **5 passed**, covering six formats, resume/completion, linked AI/speech context,
  mobile controls, ordinary-account denial, all 52 modules and 181 mapped lessons.
  The expanded real check-plan case additionally passed on its own.
- All 34 new listening scripts and the exact 600-character boundary produced
  valid bounded WAV audio. This proves synthesis, not human phonetic quality or
  authentic multi-speaker listening competence.
- ESLint, TypeScript and frontend production build passed. Extended-writing tests
  accept 8,000 Unicode characters, reject 8,001, enforce a bounded route-specific
  envelope and retain other AI limits, CSRF and cross-user denial.
- Final full backend suite: **384 passed, 16 optional integration tests skipped**
  in 499.42 seconds. The separate guarded real-service run above passed all 34.
  Two dependency deprecation warnings remain non-blocking. The initial full run
  found one outdated 4,001-character rejection expectation after the intentional
  8,000-character writing change; it was corrected to test 8,001 and the complete
  suite rerun successfully. No failing assertion was disabled.
- The owner's earlier physical microphone/transcription/French tutor-playback
  confirmation is historical evidence. No new physical hardware test is claimed.
- The real owner sign-in page is ready at `http://127.0.0.1:3000/login`; direct
  browser acceptance is pending the owner entering their own credentials. No
  password reset, impersonation or synthetic progress in that account was used.

Final normal-mode shutdown returned success; API and speech lifespan shutdown
completed, the owned infrastructure/daemon stopped, and the next static preflight
passed with C: 36.19 GiB / D: 177.78 GiB free. The normal launcher then reached
`ready` again; post-restart protected main/M08 signatures still matched. Audit-only
8001/8002 APIs shut down cleanly. Normal personal services remain running for the
owner, with pre-existing Ollama left in place. Listeners were verified loopback-only.
Personal Ubuntu remains stopped; no new matching System storage warnings were
returned by the bounded event query. That query is not a hardware-health guarantee.

Technical owner acceptance is **not fully closed** until the owner completes the
pending browser sign-in. Automated authentication/persistence and read-only account
permissions pass, but do not substitute for entering the owner's credentials.

### Educational limits

Technically validated draft input is available in every mapped module. This is
not a claim of comprehensive A0–C2 educational completeness, independent qualified
French-teacher approval or empirical CEFR calibration. The audit keeps remaining
gaps visible: limited spontaneous/varied-speaker audio, independently rated extended
production and unseen transfer, fuller lexical/grammar depth in some modules, and
calibrated diagnostic/module/level-end performance thresholds. The new model is
one original AI-assisted example, not an exclusive answer key or human approval.
Future bridges are staged precisely because they need a separate review/import
decision. The source audit still identifies no dedicated scripted listening item
in `a1-01`, `a1-04` and `a1-09`, and no linked structured grammar-rule object in
12 modules (prose teaching can still be present). The five future bridges fill
the source-level dedicated writing gaps, but their activities are not yet live
in main. No proficiency certification or acoustic pronunciation score is claimed.

Historical evidence follows; older pending-import/service/account statements must
not be interpreted as the current state.

## Startup blocker resolved and live audit completed — 23 November 2026

This checkpoint supersedes the blocked-runtime/PostgreSQL/audio statements below.
All 80 curriculum manuscripts remain staged; no additional main import occurred.

### Confirmed port cause and guarded restoration

Supported Windows TCP tables and `netstat` showed no port-8000 owner. `netsh`
showed no relevant port proxy or IPv4/IPv6 excluded range. The saved `ready` record
had no live owner; Docker and both WSL distributions were stopped. Python probes
with 0.3s and 1s deadlines returned inconclusive `10035`; a 3s probe returned
explicit refusal `10061` after 2.031s. An independent .NET TCP probe returned
active refusal after 2.044s. The false negative was therefore the guard's deadline
expiring before Windows delivered the refusal, not a healthy competing backend.

The bounded wait is now three seconds. Only explicit refusal still proves closure;
an active connection, timeout, permission error or unavailable inspection continues
to refuse startup. Regression cases cover all these outcomes. No firewall,
reservation or process was changed to make the check pass. The existing exclusive
lock/PID/WSL review archived the orphaned state without claiming an earlier graceful
shutdown. Static preflight passed with C above 30 GiB and D above 50 GiB, and all
staged pack hashes plus existing database/audio backup manifests verified.

The existing launcher started only its three approved existing infrastructure
containers and native frontend/API/speech children. Immutable container identities,
data mount destinations, database identity/revision, preview UUID/learner role,
readiness and installed Ollama model checks passed. Container ownership now includes
approved containers automatically resumed by a Desktop instance started by this
run, so they are not left running after the bounded audit. Pre-existing daemon
containers remain unowned. Launcher safety/ownership regressions: **31 passed**.

PostgreSQL reported its prior interrupted shutdown, performed normal startup WAL
recovery and became ready. No filesystem repair, database restoration into main,
reset, protected migration or unsafe fallback ran. No matching new Windows System
storage errors were found by the bounded query; this is not a general hardware
health certification. Personal Ubuntu remained stopped throughout.

### Fresh main/M08 preservation and recoverable backup

Full read-only table-signature comparisons before and after live testing matched
the recorded main and M08 baselines with **no differences**. The pre-existing
baseline excludes only `user_sessions.last_used_at`; other session fields/counts
remain included. No baseline was replaced to accept differences. Whole-database
counts retained:

| Database | Users | Lessons | Exercises | AI conversations/messages | Speech sessions/turns |
|---|---:|---:|---:|---:|---:|
| main `fluentloop` | 2 | 101 | 470 | 8 / 16 | 6 / 8 |
| historical M08 | 10 | 23 | 81 | 31 / 12 | 15 / 7 |

The confirmed personal UUID remains an active verified learner. Main preview
availability is A0=7, A1=34 and 12 each A2–C2. Ordinary learner denial passed, and
all 29 staged release keys are absent from main. Existing progress, writing,
account, AI/voice and frozen-session records remain covered by the baseline check.

A new consistent main backup was created and successfully restored **only into a
new disposable PostgreSQL database**. Private artifact:
`.publication-private/live-runtime-20261123/fluentloop-before-staged-rehearsal.dump`,
552003 bytes, SHA-256
`8f5f4d9c5655d6692ade8d0e1c3ac553ee2d453c1533b042fbf6497c75c79212`.
Archive listing, restored schema and final file hash passed. Earlier backups and
audio copies were reverified without overwrite.

### All staged material rehearsed and listening runtime checked

On the fresh main restore at revision `20261115_0016`, **80 lessons, 150 scored
exercises and 29 open transfer tasks** imported as drafts. Duplicate imports reused
the immutable releases. All 150 intended/deliberately wrong answer-key checks,
prerequisite links and validated foreign keys passed. Every pre-existing restored
row remained unchanged, including the original 101 lessons and learning records.
Disposable final totals were 181 lessons/620 scored exercises; these are not main
totals. Sanitized evidence: `docs/learning/STAGED-POSTGRES-VALIDATION.json`.

All **34 staged listening scripts** and an exact 600-character boundary synthesized
into valid RIFF/WAV below the existing 6 MB cap. No learner records were created by
these private-worker calls. This proves the synthesis contract, not French
pronunciation quality or authentic multi-speaker comprehension.

### Fresh regression results

- Full backend: **375 passed, 16 skipped**, two deprecation warnings, 552.42s.
- Guarded real PostgreSQL/Ollama/Whisper/Piper suite: **34 passed**, two warnings,
  428.69s. These run separately from the default suite's skipped live tests.
- Standard browser suite: **25 passed, 36 optional tests skipped**.
- Dedicated historical admin-fixture browser suite: **7 passed**.
- Real learner-only preview browser suite: **5 passed**, 31.0s, including the six
  exercise formats, Piper audio, saved feedback, resume/completion, ordinary denial,
  owned AI/speaking context, mobile controls and all 52 modules/181 source lessons
  across seven stages on the disposable API. Account level was not changed.
- ESLint, TypeScript, final isolated Next.js production build and whitespace checks
  passed. A reserved `module` variable name in the added test was renamed after
  lint caught it; assertions were unchanged. Browser totals are separate invocations.

Private logs and machine-readable results are in
`.publication-private/live-runtime-20261123/`. Curriculum source hashes are unchanged.
No tests, access checks, rate limits or output-size guards were disabled.

### Verified shutdown and remaining limits

Both audit-only test APIs exited through their lifespan shutdown. The launcher
gracefully stopped its application processes, Mailpit/Redis/PostgreSQL and Docker
Desktop. PostgreSQL logged `database system is shut down`; launcher state is
`stopped`. No audit-owned process or Docker Desktop/backend remained, and both
WSL distributions were stopped. Pre-existing Ollama retained its original daemon
and app PIDs and was left running. Unrelated processes were not stopped.
Final observed free space was 39,144,452,096 bytes on C and 190,903,930,880 on D.

The 52-module source map still does not establish comprehensive skill mastery.
Qualified linguistic, phonetic and pedagogical review, empirical assessment
calibration, authentic varied-speaker listening and independently rated productive
skills remain outstanding. All 80 lessons/150 exercises/29 transfer tasks remain
unpublished and staged, with separate authorization required before main import.
No commit, push, public deployment, lesson publication or destructive protected
database operation occurred.

## All previously empty module slots authored — 23 November 2026

This checkpoint supersedes the earlier 17-empty-module and 29-staged-lesson
figures. It does not claim that all CEFR competencies are adequately covered or
that a complete educational programme has received qualified approval.

### Exact source coverage and preservation

All **52/52 planned modules now have authored input; 0 remain source-empty**.
The newly populated slots are A2-05/06/07/08, B1-05/06/07/08, B2-06/07/08,
C1-05/07/08 and C2-05/06/08. The existing module order remains acyclic and all
references are unique. Each new module has reading/grammar/vocabulary, a linked
scripted listening/integration lesson, and an open transfer/assessment lesson.
The latter requires both inputs; the second input requires the first.

The new separate completion batch contains **51 lessons, 102 scored exercises and
17 open writing/speaking tasks**, with 17 structured grammar rules and 51 linked
contextual lexical expressions. B2–C2 target counterargument, conditional
commitments, methodological limits, prosody, humour, presupposition, ambiguity,
source mediation and audience-sensitive formal writing. Cumulative modules use
new practical or interpretative dossiers and separate review criteria.

The earlier 29 staged lessons/48 exercises/12 transfer tasks are unchanged; their
validation-manifest source hashes were reverified. Total staged material is now
**80 lessons, 150 scored exercises and 29 transfer tasks**. The learning map has
181 unique lesson references: 101 main-source and 80 staged. No additional main
import is authorized or performed. The main database was last verified at
101 lessons/470 exercises. No protected learner record, role, M08 record or prior
backup was intentionally written or replaced by this work. Existing backup/audio
manifest sizes and SHA-256 hashes were reverified offline.

### Disposable validation and audio contract

`backend/scripts/validate_missing_modules.py` accepts no protected database URL;
it creates an in-memory SQLite database with enforced foreign keys. After seeding
all prior 130 source lessons, it imported every new pack twice, verified all 102
intended and deliberately wrong answer cases and all 51 internal prerequisite
links, and compared every pre-existing table row. No earlier row changed or was
deleted. The resulting source-only database had 181 lessons and 620 objective
exercises. These are not main-database totals. Release hashes and method/limitations
are in `backend/content/completion/manifest/validated-releases.json`.

Initial source generation caught an incorrect exact-quotation key and the old
300-character listening cap before release validation; both were corrected. The
authoring definition and learner/reviewer audio endpoints now share a 600-character
limit matching the existing private Piper schema/provider. Previously imported
pack digests and frozen snapshots are unchanged. Tests accept 600, reject 601 and
recheck draft permission before synthesis. The existing RIFF/6 MB, ownership and
rate-limit checks remain. Actual playback of these new scripts is still pending.

### Service diagnosis and the blocked operation

Read-only Windows evidence shows a boot at **07:16:29 Europe/Paris on 23 November**,
Docker autostart disabled, no Docker Desktop/backend processes, and both Ubuntu
and docker-desktop stopped. No Windows TCP listener was listed for port 8000.
The prior launcher's `ready` record has no matching owner processes and is stale.
Boot plus disabled autostart is consistent with services remaining unavailable;
it does not establish how every preceding process exited or indicate corruption.

The existing `review_personal_local_state.ps1` safeguard nevertheless could not
confirm port 8000 closed through its socket check. It refused with
`Port 8000 could not be confirmed closed; no state changed.` No state override,
startup fallback, Docker reset, database/volume rebuild, filesystem repair or
service launch was attempted. The specific restoration operation stopped; unrelated
source authoring and offline verification continued.

Consequently a **fresh live main/M08 baseline comparison, PostgreSQL rehearsal of
the new batch and real audio/browser integration remain blocked**. These are not
reported as passed. Resolve the ambiguous port check using non-destructive
evidence and the verified procedure before a bounded infrastructure startup.
Do not weaken the guard, overwrite a preservation baseline or infer that a stale
`ready` file is health evidence. Private diagnostic evidence is in
`.publication-private/missing-modules-20261123/SERVICE-DIAGNOSTICS.json`.

### Fresh verification totals

- Full backend: **369 passed, 16 skipped, two deprecation warnings**, 263.41 seconds.
  The skipped environment-dependent tests require unavailable live infrastructure.
- Disposable source/import/key rehearsal: **17 modules, 51 lessons, 102 intended/
  wrong-answer checks**, idempotency, foreign keys and old-row preservation passed.
- Affected mocked browser suite: **10 passed**, 27.8 seconds.
- ESLint, TypeScript, isolated Next.js production build and `git diff --check`
  passed. No tests were disabled or assertions weakened. The earlier historical
  admin-fixture result of seven passed is retained below; it was not rerun against
  absent infrastructure and must not be described as a new live result.

### Remaining educational limitations

Authored input is not full competency coverage. Independent human linguistic,
phonetic, pedagogical and answer-key review and empirical CEFR calibration remain
pending throughout. Short exact-phrase extraction/matching items are supported
practice, not advanced-proficiency evidence. The realistic-style listening scripts
may all be read by one synthetic voice; authentic varied-speaker and spontaneous
speech, sustained interaction and human prosodic assessment remain gaps. Word
ranges, quiz completion and the experimental revision cue do not confer mastery.

See `docs/learning/COMPETENCY-AUDIT.md`, `competency-audit.json`,
`curriculum-coverage.json` and `backend/content/completion/README.md` for the
module-by-module evidence and review scope. No publication, commit, push,
deployment, protected database migration or additional main import occurred.

## Competency depth and isolated admin verification — 23 November 2026

This is a development checkpoint, not project completion or complete CEFR
coverage. No main/M08 import, publication, role change, commit, push or deployment
was performed. The main database was last verified at 101 lessons/470 exercises.

### Coverage and authoring

The reproducible source audit now inspects every reference in the 52-module map
and the seven-stage project competency blueprint. It records source hashes,
main/staged availability, structured grammar links, vocabulary links, open writing
tasks, scripted-listening counts, input length and explicit missing evidence.
It does not equate any of those metrics with competency approval. See
`docs/learning/COMPETENCY-AUDIT.md`, `competency-audit.json` and
`curriculum-coverage.json`. This is a project design interpretation of CEFR goals,
not an exhaustive official descriptor inventory or prescribed grammar syllabus.

**17 of 52 modules still have no authored input.** Every stage remains incomplete;
even populated modules lack some skill breadth, qualified review or calibration.

The existing 14 scenario lessons/28 exercises/seven transfer tasks are unchanged:
their original validation-manifest file hashes were rechecked. A separate depth
batch adds five cohesive modules, **15 lessons, 20 scored exercises and five open
writing/speaking tasks**. A0/A1 teach classroom repair and appointment confirmation.
B2/C1/C2 use paired substantial original inputs (over 300 combined French words
per advanced dossier) and extended argument/synthesis/register tasks. Each module
has two prerequisite-linked inputs followed by productive transfer and task-specific
review criteria. All 15 passed disposable PostgreSQL import, intended/wrong answer,
prerequisite and idempotency checks while preserving existing disposable rows.
The manifest is `backend/content/depth/manifest/validated-releases.json`.

Combined staged material is **29 lessons, 48 scored exercises and 12 open transfer
tasks**. Neither batch is authorized for main import. Contextual vocabulary and
grammar notes do not replace missing structured glossary/rule records. Listening
is still scripted synthetic playback, not authentic varied-speaker evidence.
Qualified independent language, pedagogy, phonetic and CEFR review remains pending.

### Formative progression, not a proficiency award

The read-only learning-path projection now separates activity completion from
formative evidence. It uses only owned, current-version, completed full-lesson
sessions. Older versions, focused practice and zero-point sessions cannot establish
the objective-practice indicator. Same-day repetition does not count as delayed
retrieval; a later low result recommends revision despite an earlier high score.
The 80% cue is explicitly experimental and has no empirical cut-score validation.
Saved writing remains subject to qualitative review. No result automatically
grants mastery, changes the account level or locks out exploration. The UI shows
this advice and a suggested next practice link. See
`docs/learning/ASSESSMENT-AND-PROGRESSION.md` for the external calibration protocol.

### Historical admin browser fixture

The old tests read a historical fixture while targeting the learner-only personal
API. A new dedicated harness creates only localhost `fluentloop_browser_admin_*`
databases with synthetic admin/learner accounts, the expected interactive 0.1.1
lesson, matching cookies and an isolated empty Redis DB. Fixture paths are explicit;
the old fallback remains compatible. All seven historical assertions passed in
40.0 seconds. No assertion, authentication rule, rate limit or permission gate was
weakened. See `docs/verification/ADMIN-BROWSER-HARNESS.md` for exact operation and
the preserved failed preparation attempts.

### Verification and current environment limitation

- Full backend: **365 passed, 16 skipped, two deprecation warnings**, 365.22 seconds.
- Real PostgreSQL/AI/speech: **34 passed**, two warnings, 342.22 seconds.
- Historical admin-fixture browser tests: **7 passed**, 40.0 seconds.
- Affected mocked path/assessment/persistence/offline/settings browser tests:
  **10 passed**, 19.5 seconds.
- Final next-practice/progression backend tests after the UI-link addition:
  **5 passed**, two warnings, 5.67 seconds.
- Final suggested-practice browser checks: **2 passed**, 6.7 seconds.
- Disposable-harness target guards after the connection-timeout addition:
  **4 passed**, two warnings, 0.22 seconds.
- Frontend lint, TypeScript, final isolated production build and whitespace checks
  passed. These are separate test invocations; their counts must not be added to
  the full backend total.

Evidence directory: `.publication-private/coverage-expansion-20261122/`.
The full-table main/M08 baseline and existing staged-source/backup verification
passed before the regression runs; all curriculum rehearsals used disposable
databases. On resumption, Docker's API was absent and PostgreSQL, Redis and speech
were unreachable; the native process IDs from the earlier `ready` record were no
longer present. That bookkeeping is stale, not evidence of a running application.
The waiting read-only check was interrupted without restarting infrastructure.

Consequently, a fresh live post-run main/M08 comparison and further live browser
checks remain pending. Existing backup/audio sizes and hashes and the original
14-lesson source hashes were successfully reverified offline on resumption.
No new protected-service startup or recovery operation was attempted. A bounded
infrastructure startup and ownership/storage review are needed before that final
live audit; do not rely on the stale runtime state or bypass its safeguards.

Automatic approval review previously blocked one frontend-check launch because of
a usage limit, not an unsafe-action finding. It was not bypassed. The subsequent
authorized verification launch succeeded after resumption. Qualified independent
review/rater calibration and authentic listening remain genuine external work;
the current application must not describe these drafts as human-approved or as
official CEFR certification.

## Foundation import and scenario expansion — 22 November 2026

This checkpoint supersedes the 82-lesson totals below. The owner authorized only
foundation releases A0 0.3.0 and A1 0.3.2 (19 lessons, 96 exercises). These were
imported as unpublished personal drafts after graceful writer shutdown, a fresh
consistent database/audio backup, archive verification and successful restoration
and import rehearsal in a newly named disposable PostgreSQL database.

The backup is retained in `.publication-private/foundation-import-20261122/`:
`fluentloop-after-curriculum-import.dump`, 498905 bytes, SHA-256
`75f910a255de9426caae69cc192be952e03c9b5cf7f61f9177a6d0d19e89219a`.
`BACKUP-MANIFEST.json` includes verified copied audio. Earlier backups were not
overwritten. `REHEARSAL-RESULT.json` records the successful restored-copy rehearsal;
`IMPORT-RESULT.json` records the committed atomic import and pre-existing row
digests. The importer rejected any changed source digest, duplicate fresh batch,
unexpected schema, role, active writer or changed/deleted pre-existing row.
Repeat imports inside the transaction reused the same immutable release.

Main now contains **101 lessons and 470 objective exercises**:

| Learning stage | Available main lessons | Objective exercises |
|---|---:|---:|
| A0 introductory preparation | 7 | 36 |
| A1 | 34 | 164 |
| A2 | 12 | 54 |
| B1 | 12 | 54 |
| B2 | 12 | 54 |
| C1 | 12 | 54 |
| C2 | 12 | 54 |

A0 uses A1 database storage with explicit introductory metadata; it is not a new
official CEFR level. Read-only `path_for` verification found all 101 unique lessons
through the confirmed learner's existing personal preview, across all seven map
stages. Ordinary accounts were denied all drafts. Account role, learning progress,
AI and voice history remained unchanged. Every pre-existing row was preserved by
the atomic transaction; a subsequent history/account digest check also passed.
All M08 table digests matched before and after this operation. No migration,
publication, role change, M08 import, restore into main or destructive rollback ran.
The guarded runtime restarted successfully and reached `ready`.

### Next batch remains staged

Seven new two-lesson scenario modules contain **14 lessons, 28 scored exercises
and seven open writing/speaking transfer tasks**, two lessons at every stage.
They cover a bakery, market, transport delay, housing repair, university access,
workplace evidence and administrative rhetoric. The B2–C2 tasks explicitly address
limited evidence, counterarguments, methodological qualifications, presupposition,
irony and audience-sensitive mediation. The short excerpts are still partial
practice, not complete advanced reading/listening coverage.

Current source and validated manifest are in `backend/content/scenarios/`.
Correct/wrong answer checks, prerequisite links, idempotent reuse and preservation
of all existing disposable rows passed against the fresh main restore containing
the 101 lessons. No scenario release 0.4.x exists in main. A separate authorization
is required for any future import. The initial A0 0.4.0 glossary conflicted with
the original course's canonical `merci` definition in regression testing; the guard
rejected it. Corrected A0 0.4.7 reuses the canonical definition, and the earlier
source is archived without being rewritten or imported into main.

The map now has 115 unique references: 101 available and 14 staged. Coverage at
every stage remains incomplete. Qualified independent human language/pedagogy/
phonetic review and CEFR calibration are pending. Reference-informed AI editorial
review is not human approval. Synthetic scripted listening does not establish
native-speed, multi-speaker comprehension. Formative scenario checks and advisory
AI writing feedback do not replace calibrated diagnostic/module/level-end exams.
No number of completed lessons automatically awards a CEFR level.

### Fresh regression results

- Full final backend suite: **353 passed, 15 skipped, two deprecation warnings**,
  exit zero. Totals are counted from pytest's progress markers because the
  repository's quiet configuration suppresses its numeric totals line.
- Real PostgreSQL/Ollama/Whisper/Piper regression suite: **34 passed**, two
  deprecation warnings, 396.16 seconds.
- Standard browser suite with its intended fixture configuration: **25 passed,
  36 optional tests skipped**, 58.3 seconds.
- Four current real personal-preview browser journeys passed: six exercise
  formats/Piper audio/saved feedback/resume/completion; ordinary learner denial;
  owned grammar AI/speech context; mobile keyboard/reset/layout.
- ESLint, TypeScript, isolated frontend production build and `git diff --check`
  passed. No dependency or test-security policy was weakened.

The first backend invocation overlapped a map edit and retained the old expected
101-reference assertion in memory; the final full invocation collected stable
source and passed with 115 unique references. The new scenario regression also
exposed the genuine `merci` compatibility issue described above, subsequently
fixed and covered by the final full run.

An exploratory browser invocation enabled the historical M08 admin-fixture tests
against the current learner-only API. Seven tests failed to authenticate because
that stack does not contain their expected admin fixture. The four current real
personal-preview tests and 25 standard tests passed in that invocation. A repeated
standard run then encountered two 429 failures after the failed legacy logins had
consumed the disposable API's IP login budget. The test API was gracefully stopped
and restarted with a different verified-empty Redis test database, without clearing
any existing cache or altering rate limits. The unchanged standard suite then
passed. The legacy fixture-specific browser tests remain unverified under their
own dedicated stack at this checkpoint; they were not disabled or rewritten.

The disposable API was gracefully stopped after testing. Main access, history and
backup integrity were rechecked successfully. The personal runtime remains ready
at the time of verification, subject to the launcher session staying alive. Free
space was 38,465,716,224 bytes on C: and 190,920,290,304 bytes on D:, above both
configured reserves. No Ubuntu boot, recovery operation, Git commit/push, public
deployment or curriculum publication was performed.

## Zero-to-C2 checkpoint — 22 November 2026

This checkpoint supersedes earlier statements below that the 72-lesson release
was not imported. It is a progressive implementation checkpoint, not a claim of
complete CEFR coverage or certified proficiency.

### Authorized main import and preservation

After a fresh verified consistent backup, release 0.2.1 added 72 unpublished
lessons and 324 exercises to `fluentloop`. The transaction compared every
pre-existing public-table row before commit: no original row changed or was
deleted. Idempotent reuse and source digests passed. The personal account remains
a learner; the separate M08 database matches its preservation baseline.

The main database now has 82 lessons and 374 exercises: 22 A1 lessons with 104
exercises, and 12 lessons with 54 exercises at each of A2, B1, B2, C1 and C2.
All imported curriculum remains unpublished. Main-database A0 content is pending.

Private evidence is in `.publication-private/zero-c2-import-20261122/`, including
`IMPORT-RESULT.json`, `preexisting-record-preservation.json`,
`authorized-access-readonly.json` and `m08-preservation.json`.
A second verified post-import backup is in
`.publication-private/zero-c2-postimport-20261122/`:
`fluentloop-after-curriculum-import.dump` (498906 bytes), SHA-256
`879d000014e8b6a3f00f167ca12b20572567db659e93d5d8aa82f33c62175cee`.
Its manifest includes preserved audio evidence. Verification after the actual
guarded restart found unchanged table counts and matching learning/audio records;
only the permitted session last-used timestamp changed, checked against archive.

### Learning path and next staged batch

`/learning-path` exposes A0–C2, 52 planned modules, objectives, prerequisites,
available/completed/remaining lesson activities, revision goals and assessment
links. Writing activities use the existing writing workflow. Cross-level browsing
and assessments preserve the saved account level. AI/voice entry points require
the matching saved level and explain how to change it explicitly.

New foundation releases contain 7 A0 lessons/36 exercises and 12 additional A1
lessons/60 exercises. All 19 lessons/96 exercises passed disposable PostgreSQL
validation, intended/wrong-answer checks, prerequisite checks and idempotent reuse.
The validated manifest is
`backend/content/foundations/manifest/validated-releases.json`.
These later releases are staged only; separate main-import authorization is
required. A0 is introductory, not an official CEFR level.

Coverage remains incomplete at every stage. Advanced extended texts, nuanced
listening, broader real-life domains, calibrated diagnostic/module/level-end
assessments and qualified human language/CEFR review remain outstanding. Current
counts must not be interpreted as sufficient evidence of level mastery. See
`docs/learning/curriculum-coverage.json` for the explicit gaps.

### Verification results and limits

- Full backend invocation: 344 passed, 16 skipped, two warnings.
- Subsequent affected tests after the final writing/progress changes: 33 passed,
  two warnings; this is a separate invocation, not an additional full-suite count.
- Real PostgreSQL/AI/speech regressions: 34 passed, two warnings.
- Browser suite: 25 passed, 36 optional historical tests skipped.
- Real interactive browser journeys: four passed. A later six-check invocation
  passed five and failed listening audio because the worker was paused for backup.
  After guarded restart, the unchanged six-format/Piper/resume/completion journey
  passed on its own (one passed); no test was weakened to resolve that failure.
- ESLint, TypeScript and isolated frontend production build passed.
- Physical microphone/transcription/tutor/playback acceptance remains verified by
  the owner's explicit confirmation, not an automated physical-device claim.

Startup initially encountered orphaned private runtime bookkeeping with no live
owner. An audited stopped-state reconciliation was performed only after process,
port, lock and WSL checks; no force-kill or filesystem recovery was used. The new
`review_personal_local_state.ps1` provides the same conservative explicit review
workflow. Normal startup still fails closed. The latest guarded restart reached
`ready`; daily use requires keeping the launcher's PowerShell session open.
This does not guarantee availability after the hosting session ends.

No commit, push, deployment, curriculum publication, M08 modification, schema
migration or future-batch main import was performed at this checkpoint.

## Final acceptance — 22 November 2026

This final section supersedes the earlier checkpoints retained below.

**Physical voice workflow: verified by owner confirmation.** The owner explicitly
confirmed successful microphone recording, visible French transcription, an AI
Tutor response and clearly audible French tutor playback. This is human acceptance
of the current setup, not an automated observation or pronunciation certification.

### Startup, shutdown and persistence

An additional bounded real stop/start cycle completed using the existing scripts.
`stop_personal_local.ps1` returned success and state became `stopped`. PostgreSQL
logged normal shutdown and readiness after restart. Guarded startup returned to
`ready`, with frontend HTTP 200 and API readiness confirming PostgreSQL and Redis.
Only the owned application processes and three existing infrastructure containers
were stopped/restarted. No Ubuntu boot, migration, import or volume removal ran.

A fresh consistent custom-format PostgreSQL backup was created before the cycle;
its archive listing and SHA-256 were verified. Current audio files were copied and
verified by size/hash. Every main table digest matched across the cycle except
authentication usage bookkeeping. Archive-to-live comparison proved that only
`user_sessions.last_used_at` changed: all other columns of all six session rows
matched. All audio hashes matched. The prior historical records and complete M08
database also match their preserved projections. New owner activity was retained,
not discarded to force equality with older whole-table counts.

The main database contains the same 10 draft lessons, plus 8 AI conversations,
16 AI messages, 6 speech sessions, 8 speech turns and 3 audio metadata records.
These records survived restart. No new 0.2.0/0.2.1 curriculum exists in main.

Private evidence: `.publication-private/final-personal-verification-20261122`.
The fresh archive is `fluentloop-after-voice-acceptance.dump`, 363,796 bytes,
SHA-256 `DE30C9D18BB03C00DF3ACA758D8E8BA9A62E97FCB63A18125BDEF0B561C31A96`.
`BACKUP-MANIFEST.json` covers the archive and copied audio. The archive received
format/listing and hash checks; it was not restored into the main database.
Older recovery backups/clones were not modified. VHDX sizes/timestamps match the
preserved checkpoint; full VHDX hashes were not rerun for this application check.
The migrated Ubuntu VHDX metadata remains at its last diagnostic-boot checkpoint.
No relevant new Windows System storage warnings/errors were found during the
bounded cycle. C: remained above 30 GiB and D: above 50 GiB. One successful cycle
is evidence of this configuration, not a guarantee of indefinite uptime.

### Final staged curriculum review

The reference-checked second-pass AI review is complete. Release **0.2.1** has
**72/72 lessons and 324/324 exercises passing draft validation**, with 12 lessons
at each level A1, A2, B1, B2, C1 and C2. The 20 affected curriculum/assessment
tests passed. All saved keys accept intended answers and reject wrong answers;
checks cover semantic links, balanced choice positions, Unicode, persistence,
ordinary-account denial, legacy digests and immutable releases. Disposable
PostgreSQL validation confirmed counts, draft status, source hashes, repeat-import
reuse and preservation of the older 0.2.0 test release. No main or M08 import ran.
Corrections are detailed in `backend/content/personal/README.md`.

**0/72 have independent human sign-off.** CEFR labels remain provisional practice
targets, particularly the short advanced readings and scaffolded drills. Qualified
FLE calibration and independent linguistic, phonetic, pedagogical, answer-key and
licensing reviews remain outstanding for curriculum approval. No unresolved
structural, deterministic answer-key or source/import consistency error was found.
These review gates do not block personal use of the existing A1 lessons. Import
and publication require separate owner authorization and remain unperformed.

### Scope and remaining limits

| Final check | Result |
|---|---|
| Final complete isolated backend suite | **330 passed, 16 optional skips, 2 dependency deprecation warnings**, 286.99 seconds |
| Reviewed curriculum/assessment selection | **20 passed**; included in the full suite, not additive |
| Revised curriculum PostgreSQL validation | 72 lessons / 324 exercises; only disposable DB; older release preserved |
| Dependency audit rerun | **0 known vulnerabilities**; no package changes |
| Real personal shutdown/restart | Passed; normal PostgreSQL logs, launcher ready, API DB/Redis connected |
| Restart data/audio preservation | Passed; only the verified authentication usage heartbeat changed |
| Physical voice acceptance | Owner-confirmed microphone, ASR, Tutor response and French playback |
| Earlier same-day frontend checks | Production build, ESLint and TypeScript passed; frontend code unchanged in this final check |
| Earlier same-day browser / real inference checks | 23 ordinary browser tests passed; four live lesson checks passed across runs; 34 PostgreSQL/inference checks passed |

The 16 backend skips include environment-specific PostgreSQL tests exercised in
the separate integration run and the numpy-dependent case exercised in the speech
environment. They are not new disabled tests. Earlier browser optional skips
require distinct historical environments. Two Starlette/AnyIO deprecations remain
non-failing maintenance items. No full repeat build/browser run was needed after
documentation-only changes; curriculum revisions received fresh affected and full
backend validation.

The project remains personal and local only. No commit, push, deployment, cleanup,
filesystem repair or protected database migration occurred in this final check.
Existing uncommitted implementation changes and all previous backups are retained.
The runtime is left ready at `http://127.0.0.1:3000/login`. Start/stop instructions
are in `docs/learning/personal-local-operation.md`. Full automated-suite evidence
is recorded below with its dates and environment limits; counts are not additive.
Optional historical-environment tests remain explicitly skipped, not disabled.

## Earlier 22 November 2026 acceptance checkpoint

This section supersedes the historical runtime-pending status below. The existing
main database was upgraded in the separately authorized/rehearsed operation to
`20261115_0016`. The guarded personal launcher has reached ready state on
`http://127.0.0.1:3000/login`, using existing PostgreSQL/Redis/Mailpit containers,
native FastAPI/Next.js, Ollama and one speech worker. No Ubuntu boot is required.
Owner-driven password reset/sign-in succeeded; the signed-in dashboard and ten
existing unpublished A1 lessons were observed. No synthetic activity was performed
on the real learner account.

The confirmed UUID is configured only in ignored local configuration. The account
retains the learner role, with no author, reviewer, publisher or administrator
grant. Global administrator draft preview remains disabled. Independent curriculum
reviews remain pending. The launcher performs continuous storage reserve checks.

### Current validation evidence

Evidence is retained privately under
`.publication-private/personal-completion-20261122-175037`.

| Check | Result |
|---|---|
| Complete isolated backend suite | 329 passed, 16 optional checks skipped; two deprecation warnings |
| Separate PostgreSQL integration and real inference suite | 34 passed; real Ollama and Piper/Whisper paths enabled |
| Speech decoder in the speech environment | 4 passed |
| Targeted curriculum/assessment/launcher selection | 36 passed before the added full-key roundtrip regression; included in the later full suite |
| Full ordinary browser suite | 23 passed, 36 optional historical-environment checks skipped |
| Real PostgreSQL browser journey | All four checks passed: six formats/audio/persistence, ordinary denial, linked Tutor/voice navigation, mobile controls; final mobile check run separately after a render-wait correction |
| Final ESLint / TypeScript | Passed with generated `.next-e2e` output excluded from source lint |
| Next.js 16.4.6 production build | Passed, all 39 static pages generated |
| npm audit | Zero known vulnerabilities |
| Main learning/content/AI/voice and complete M08 table hashes | Match verified pre-runtime baselines in read-only transactions |

The isolated backend suite uses disposable SQLite/fakes; the separate PostgreSQL
suite and browser journey provide distinct runtime evidence. Counts overlap and
must not be added as unique test totals. Optional historical WSL/demo fixtures
were not enabled against protected databases. Physical microphone capture and
human listening/recognition quality still require the owner's acceptance check.

### New curriculum review inventory

`backend/content/personal` contains six immutable 0.2.0 manuscript packs: 12 draft
lessons per level A1, A2, B1, B2, C1 and C2 (72 total), 324 objective exercises,
18 open writing tasks, 18 grammar topics and 54 lexical expressions. All six
objective formats are covered. All 324 saved answer keys are checked through the
real grader; six-level session tests cover persistence and denial. A disposable
PostgreSQL import verified counts and repeat-import reuse. Legacy release digests
remain compatible; shared lexical meanings and immutable releases are protected.

**No new manuscript was imported into main `fluentloop` or M08.** Separate owner
review/import authorization is required. These short practice drafts do not form
an independently reviewed or exhaustive CEFR syllabus. All five human-review
categories remain pending; see the curriculum README for scope and limitations.

### Fixes found during acceptance

- Replaced external Google font fetching with local system fonts for offline use.
- Patched Next.js/eslint-config-next to 16.4.6; lockfile audit is clean.
- Fixed launcher Alembic discovery imports without running migrations.
- Set the owned Next wrapper's Turbopack environment before initialization,
  avoiding Cache Components manifest failures during actual login rendering.
- Added separate browser-test build output and ignored only generated files in
  Git/ESLint; bounded browser workers to avoid cold-compilation contention.
- Allowed the existing real lesson browser tests to select an explicit disposable
  fixture and use the actual origin. Reset verifies the full original tile set.
- Added optional grammar/glossary authoring through the immutable draft importer,
  including lesson-specific grammar metadata required by frozen snapshots.

An initial test API setup loaded settings too early and returned registration
503s; its environment setup was corrected before the successful full browser run.
Repeated synthetic logins later triggered the existing limiter, so the final live
journey uses a separate empty test Redis namespace rather than disabling limits.
No protected database restoration, cleanup, curriculum publication, deployment,
Git commit or push occurred.

The mobile assertion waits for rendered exercise controls before capturing the
original tiles. Its final isolated rerun passed after the other three checks had
passed in the preceding live run. The four outcomes are not represented as one
single green invocation. Repeated-login rate limiting was observed and retained.

### Daily acceptance and remaining owner checks

Use `scripts/start_personal_local.ps1 -CheckOnly`, then the approved startup
switches documented in the operation guide. Keep the supervisor console open.
Open `http://127.0.0.1:3000/login` and use the password you chose in the local
reset flow. Mailpit at `http://127.0.0.1:8025` receives local reset/verification
messages; do not paste passwords or reset tokens into chats.

For final physical acceptance, open an existing A1 lesson, ask the Tutor a short
French question, then use Speak to record a short sentence. Grant microphone
access yourself, review the transcript, and listen to playback. Confirm the
activity appears after refreshing history. Those deliberate learning actions
belong to the owner; automated tests use synthetic accounts. Stop via
`scripts/stop_personal_local.ps1` in a second console; no volume deletion occurs.

The personal runtime was ready at final verification. Only the disposable test
API was stopped afterward. Latest measured reserves were approximately 35.93 GiB
on C: and 177.97 GiB on D:. These are point-in-time readings, not safety guarantees.
Main and M08 preservation hashes remain available in the private evidence report.
New curriculum import and independent reviews remain separate approval gates.

## Historical implementation checkpoint

20 November 2026. Source implementation completed; protected-runtime acceptance
is **pending**, not claimed complete. No commit/push or public deployment occurred.

## Changes

- `scripts/start_personal_local.ps1` / `stop_personal_local.ps1`: paired Windows
  entry points, with the Python supervisor and owned Uvicorn/Next wrappers.
- Explicit protected-runtime approval and recovery switches; private JSON config;
  disk, identity, mount, schema, health and port checks. No automatic migration,
  import, model download, image build, container recreation or deletion.
- Owned-process stop markers and live Windows supervisor lock; graceful app exit
  before owned dependency shutdown. Unrelated workloads remain untouched; failures
  require manual review rather than force-kill/reset.
- Development/loopback-only immutable-UUID learner allowlist, default disabled.
  Existing preview snapshots, grading, revocation, progress and published-XP
  exclusions reused. Authoring/review-console permissions separated from learning.
- Private config template, security documentation and daily-operation guide.

## Verification executed

| Check | Result |
| --- | --- |
| Broad isolated backend regression selection | **251 passed**, 167.22 s |
| Final personal-preview / launcher selection | **26 passed**, 17.46 s |
| Final config-error and disk-gate refinement | **8 passed**, 7 deselected |
| PowerShell parser, Python AST, Node syntax | Passed |
| Unapproved startup invocation | Refused before config/service access, as expected |
| Git diff whitespace check | Passed |

Selections overlap; these counts are not additive unique-test counts. The broad
selection covered auth, personalization, interactive lessons, grammar, study/
vocabulary, assessments/reading/writing, Tutor/coach, speech, motivation, authoring
and independent review. Final affected tests include all six lesson exercise
formats, normal learner/other-user denial, production/nonlocal-origin denial,
revocation with retained frozen answers, no admin/author/review grant, no draft XP,
draft-linked Tutor/voice history and fake-provider transcription/TTS integration.

Launcher tests include fake Docker/low-storage gates, dependency stop ordering,
stuck-writer preservation, a real disposable loopback Uvicorn lifespan shutdown,
and actual pinned Next 16.4.3 initialization/graceful exit on a disposable project.
No protected frontend/API/container/database was launched. Next fixture work was
separate from the real frontend. Tests do not establish PostgreSQL durability,
browser end-to-end UX, real inference/ASR quality or physical microphone behavior.

The first sandboxed run stalled TestClient/child-server operation; it was
interrupted and rerun outside that Windows app sandbox with only isolated SQLite,
fake Redis/mail/providers and disposable loopback fixtures. Two initial new-test
assertions were corrected to the actual `answered_exercises` response field and an
explicit development environment. Final affected tests pass without skips/weakening.
Two existing Starlette/httpx/AnyIO deprecation warnings remain; dependency upgrades
were not mixed into this change. No full production build was run while C: is low.

## Protected-state evidence

- Ubuntu-24.04 and docker-desktop remain **Stopped**; Docker process count zero.
- Root private `.env` SHA-256 matches the Phase 10A backup copy.
- Phase 10A project manifest hash matches its recorded backup index.
- No personal runtime config exists; no learner UUID or grant was assigned.
- Original Ubuntu VHDX remains 21,146,632,192 bytes, last write
  2026-11-16 14:05:28.5545813 UTC. This is metadata evidence, not a fresh full hash.
- Latest measured C: free 17,808,183,296 bytes (~16.59 GiB); D: free
  215,810,117,632 bytes (~201.00 GiB). Earlier audit C: was ~19 GiB; the change was
  observed, but this verification did not attribute it to a particular component.
- No protected DB writes, source cleanup, model removal, VHDX operation, migration,
  publication, deployment or backup removal occurred. Expected source changes are
  uncommitted. Test artifacts remain ignored/private.

## Account lookup and remaining gates

The owner supplied the personal email privately and requested email/UUID/role
confirmation before any grant. Loopback PostgreSQL candidates 5432, 5433 and 55432
were unavailable. No protected service was started to perform SQL. The actual
lookup and UUID confirmation are therefore **pending**. No account was inferred
from a screenshot, created, modified or elevated. Public documentation contains
no personal email/UUID/credentials.

Before daily use: restore C: headroom using the separately approved supported
storage plan; resolve Docker startup prevention; authorize a read-only account/
database/history/audio-store/maintenance audit; confirm the exact UUID and
configure private existing container IDs/volumes/database; separately authorize
runtime start. The launcher enforces 30 GiB C: / 50 GiB D: minima. It does not
migrate Ubuntu or Docker or change Ollama storage. Verified recovery backups,
models and volumes remain protected.

## Final acceptance

See [the operation guide](../learning/personal-local-operation.md) for exact config
steps and commands. After the gates above:

1. Static preflight; then explicitly approved Start. Use the displayed loopback
   URL (default `http://127.0.0.1:3000/login`).
2. Log into the confirmed existing learner; compare profile/history baseline.
   Exercise Lessons, Grammar, Vocabulary and reading/listening/writing assessments.
3. Verify scoped unpublished draft access and ordinary learner denial. Save/resume
   an exercise, inspect recommendations/analytics and published-content motivation.
4. Ask Tutor a French question. Perform the single manual microphone/transcript
   review/Piper playback session and reopen saved history.
5. Stop gracefully, restart with approval and verify persisted progress and
   conversations; stop afterward. No data reset or publication to achieve a pass.
