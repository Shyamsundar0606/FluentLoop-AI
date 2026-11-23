# Personal local-only operation

FluentLoop AI is intended here for private daily French learning on Windows.
No public hosting, publication or major launch milestones are needed. Existing
curriculum, AI, voice, assessment, history and security features are retained.

## Current status

The launchers and learner-only preview gate have been exercised locally. The
confirmed learner account uses the existing main `fluentloop` database at revision
`20261115_0016`; its UUID is allowlisted only in ignored private configuration.
The account remains a learner. After separate authorizations and verified backups,
the personal database now contains 181 lessons: 12 introductory A0, 39 A1 and 26
each A2–C2, with 620 objective exercises and 50 open writing/transfer task lessons.
Curriculum remains unpublished. A0 is
stored as introductory A1 preparation, not a new database CEFR level.
Ubuntu storage has already been relocated to D: through the authorized recovery
process. Local source changes are uncommitted. Later batches require separate
review/import approval. The exact 14 scenario, 15 depth and 51 module-completion
lessons were imported after direct owner confirmation, fresh verified backup,
disposable restore rehearsal and preservation checks on 23 November 2026. All 34
new listening scripts synthesized successfully. Five subsequent unscored A0/A1
writing bridges remain staged and require separate import approval; a C2 model
companion remains a review-only file. Qualified human language/phonetic review
and empirical assessment calibration remain pending.
Use `/learning-path` for the seven-stage, 52-module map and `/checkpoints` for
52 module and seven level-end review plans. These reuse practised assessment
components and provide qualitative writing/speaking criteria; they are not unseen
or calibrated examinations. No aggregate proficiency score is manufactured.

## Daily start and stop

In Windows PowerShell:

```powershell
cd "D:\shyam\Projects\FluentLoop AI"
.\scripts\start_personal_local.ps1 -CheckOnly
.\scripts\start_personal_local.ps1 -ApproveProtectedServices -RecoveryPrerequisitesSatisfied
```

Keep the startup console open. Visit <http://127.0.0.1:3000/login> and sign in with
the existing personal account. Do not put the password in a chat or script.
If the password is forgotten, use **Forgot password** and open the existing local
Mailpit inbox at <http://127.0.0.1:8025>. Follow the reset link yourself and enter
the new password privately; do not share the reset link or password.
In another PowerShell console, stop the owned runtime gracefully:

```powershell
cd "D:\shyam\Projects\FluentLoop AI"
.\scripts\stop_personal_local.ps1
```

Normal startup never imports curriculum or executes Alembic migrations. The
explicit `-InfrastructureOnly` maintenance mode starts only the approved existing
database/Redis/Mailpit infrastructure; it does not start application writers.
Never use it to bypass a failed storage, identity, revision or ownership check.

Required daily services are Next.js, FastAPI, PostgreSQL and Redis. The launcher
also uses the existing Mailpit container for verification/reset mail. Native
Windows Ollama supplies AI features; one Faster-Whisper/Piper worker supplies
speech. Text-only use can explicitly omit AI/speech with the private JSON flags.
No personal Ubuntu boot or additional preview stack is needed to study.

## Private setup before the first authorized run

1. Complete the recovery/storage review. The launcher requires at least 30 GiB
   free on C: and 50 GiB on D:. These conservative thresholds are not guarantees.
   Use the existing backup-first native Ubuntu relocation plan if approved;
   never manually move a registered VHDX. Keep models, Docker volumes, learner
   records and all verified recovery copies. No cleanup is part of these scripts.
2. In an approved read-only database window, confirm the intended database,
   existing account/history, schema head and current audio store. Check pending
   account-erasure jobs and audio-retention settings: normal API startup runs
   existing maintenance. Do not use a disposable demo database as the personal DB.
3. Copy `scripts/personal-local.example.json` to the ignored private location
   `.publication-private/personal-local/config.json`. Fill the independently
   verified database URL/name, **full existing container IDs** for db/Redis/Mailpit,
   exact existing data-volume names and existing audio directory on D:. Do not
   create or reset any database. If historical audio exists only in a Docker
   volume, verify a separately authorized preservation/copy plan before switching
   to a native API. The launcher never silently replaces the audio store.
4. Keep `enable_personal_preview=false` and `personal_preview_user_ids=[]` until
   the owner confirms the lookup's email, UUID and learner role. Never guess a
   UUID from screenshots or provision another account. Do not put credentials in
   the public example, documentation or shell command history.
5. Retain the existing private root `.env` for other application secrets/model
   settings. No environment file is generated or overwritten. Existing speech
   token and local model assets are required. Confirm `llama3.2:3b` is the intended
   installed model. The launcher never pulls/downloads models.
6. Set `maintenance_reviewed=true` only after step 2 is reviewed and normal API
   maintenance is explicitly authorized. Do not lower disk thresholds to bypass
   recovery gates.

## Start and stop

From `D:\shyam\Projects\FluentLoop AI`, a static preflight is:

```powershell
.\scripts\start_personal_local.ps1 -CheckOnly
```

This checks configuration, disk headroom, existing WSL/Docker executables, Python/
Node dependencies, audio directory and port conflicts. It does not start Docker,
Ubuntu or databases, nor prove live database/model readiness. The example refuses
to run until placeholders are replaced. Falling below the storage reserve also
blocks startup and requests graceful shutdown during operation.

Only **after separate protected-runtime authorization and recovery prerequisites**:

```powershell
.\scripts\start_personal_local.ps1 -ApproveProtectedServices -RecoveryPrerequisitesSatisfied
```

The supervisor stays in this console. It starts Docker Desktop only if needed,
uses the explicit `desktop-linux` context, inspects existing container IDs and data
mounts, refuses other running container workloads and starts only missing approved
db/Redis/Mailpit containers. It waits for health, then checks PostgreSQL identity
and Alembic head in a read-only transaction. It never runs Alembic, imports content,
builds images, recreates containers or changes volumes.

It reuses an existing loopback Ollama server, checks the configured model, starts
one loopback speech worker if requested and verifies its authenticated health.
It starts the native API and a bounded Next development server from installed
dependencies on loopback, then checks API readiness **JSON status=ok** and login
HTTP 200. Default URL: **http://127.0.0.1:3000/login**. Keep that exact origin; do
not interchange localhost with 127.0.0.1 during a session. Personal cookies are
separate from existing demo sessions; normal login preserves the underlying user.
If AI/speech is disabled, its features may be unavailable; settings do not delete
their data. API-native HTTP configuration overrides Docker-only hostnames.

In a second PowerShell console:

```powershell
.\scripts\stop_personal_local.ps1
```

Ctrl+C in the supervisor also requests graceful shutdown. The stop command uses
the live supervisor lock and a private per-run marker, **not saved-PID killing**.
Owned frontend/API/worker processes exit first. Only containers started by this
run are stopped, in reverse dependency order with PostgreSQL last. Previously
running dependencies and native Ollama are left running. New competing container
workloads or a stuck writer stop automatic shutdown before dependent DB stops.
Docker Desktop is quit only if this run started it and no containers remain active.

Private per-run logs and recovery state remain in
`.publication-private/personal-local/`. They may contain personal diagnostic data;
never commit/upload them. A stale or `manual_attention` record blocks another run.
Inspect and resolve it with explicit operator review; the launcher never deletes
it or force-kills unknown processes. There is no force fallback, global WSL
shutdown, container/volume removal or database reset.

The Node wrapper uses the installed pinned Next 16.4.3 server's own in-process
graceful handler, avoiding Windows' forceful `kill('SIGTERM')` semantics. Its real
lifecycle is tested on a disposable Next project. A Next upgrade requires rerunning
that compatibility test. It uses dev mode, not standalone production output.

## Personal preview permission

After the lookup and explicit UUID confirmation, set the private config's
`enable_personal_preview=true` and `personal_preview_user_ids=["confirmed-uuid"]`.
The launcher supplies `ENABLE_PERSONAL_LEARNING_PREVIEW` and
`PERSONAL_PREVIEW_USER_IDS`; both default off/empty in application settings.
No DB grant, role change or schema migration is involved. Direct API configuration
can use these same trusted settings, but only in development with loopback origins
and a loopback listener.

Only allowlisted active, verified **learners** receive learning preview. Other
learners still see published content only. Existing admin preview remains separately
gated. Personal preview cannot author, inspect review packets, review or publish.
Sessions keep the existing preview marker and frozen answer snapshots. Existing
published-only aggregate and XP exclusions are retained, so preview completion does
not manufacture published-content XP. No separate published completion is claimed.
Removing the UUID hides preview history without deletion; restoring it restores
access. See `docs/security/draft-learning-preview.md`.

## Final acceptance session — after runtime authorization

1. Finish the private configuration and account confirmation above, then run the
   approved Start command. Check intended DB identity, readiness and displayed URL.
2. Log into the existing personal account. Compare profile, saved level, lesson
   progress, analytics and conversations with the private pre-start baseline.
3. Open Lessons, Grammar, Vocabulary and reading/listening/writing assessments.
   Confirm private drafts retain their labels and remain unpublished. Record any
   A1–C2 content gaps; a level selector does not establish complete curriculum.
4. Answer an exercise, save/exit and resume it; complete one review/assessment.
   Verify stored answers, recommendations and preview/published progress distinctions.
5. Ask Tutor a French question and reopen the saved conversation. Check ordinary
   published work's XP/achievements without expecting draft XP.
6. In the single physical microphone check: record a short French phrase, stop,
   review/correct/confirm the transcript, play Piper audio, and reopen voice history.
   Test text fallback. Recognition is not pronunciation scoring.
7. Run Stop, restart with approval, and verify the same saved records. Verify an
   ordinary disposable learner cannot open drafts or another user's sessions.
8. Stop gracefully and confirm database normal exit. Do not reset data to pass.

The isolated suite uses SQLite and fake dependencies; separate disposable
PostgreSQL/browser checks exercise real persistence and Ollama/Whisper/Piper paths.
On 22 November 2026 the owner confirmed successful physical microphone recording,
French transcription, an AI Tutor response and clear French tutor playback.
That is owner-confirmed acceptance of this setup, not a pronunciation score or a
guarantee for every future device/browser. See the final verification report for
the bounded real stop/start persistence check and the staged-curriculum review.
