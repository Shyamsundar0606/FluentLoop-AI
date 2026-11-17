> Latest checkpoint (2026-11-15): [current implementation and verification](CURRENT_DEVELOPMENT_CHECKPOINT.md).
> Disposable PostgreSQL/Redis and default Turbopack are now working. The older
> checkpoint descriptions below are historical and are superseded by that record.

# Project verification record

## RC verification blocked by infrastructure recovery

The [RC checklist](RELEASE_CANDIDATE_CHECKLIST.md) supersedes prior remaining-work
lists. Real Mailpit flows, erasure reconciliation, broad automated accessibility,
bounded concurrency and307 backend tests passed. Confirmed contrast/link defects
were fixed. Linux images and disposable container migrations succeeded, but the
large isolated image pull exhausted C: and Ubuntu became emergency read-only.
No root remount or filesystem repair was performed: automatic review rejected the
remount due to corruption risk. Explicit backup-first recovery approval is pending.
Public launch and final technical acceptance remain blocked.

## Latest continuation verification

The [current checkpoint](CURRENT_DEVELOPMENT_CHECKPOINT.md#latest-continuation-curriculum-privacy-and-dependency-remediation)
records scoped curriculum/provenance/prerequisite editing and reauthenticated
account export/permanent deletion. Current source head is `20261115_0016`; only
disposable databases were migrated. The adopted dependency suite passed 306 tests;
twenty additional final privacy/curriculum/migration checks passed, seventeen mocked
browser checks passed and the current real five-category assessment browser passed.
Installed Python (74 packages) and npm audits report zero known findings. A fresh
restore matched all 65 public tables. Production Compose validation and standalone
smoke passed; Linux containers/HTTPS, mail-backed full journey and wider acceptance
remain pending. This supersedes older statements below that these features were
unimplemented or that the recorded dependency advisories remain unresolved.

## Audit on 2026-11-15

The local repository began clean on `main` at `fd6198b8ee34d123df90b3e35b6e6d83d6d6666a`.
GitHub confirms PR #3 merged on 2026-11-11. The merge commit's
[push CI](https://github.com/Shyamsundar0606/FluentLoop-AI/actions/runs/43113085028)
succeeded. This is historical CI evidence for M09, not verification of later milestones.

Work is on `codex/remaining-project-readiness`. All five M10 category interfaces
are implemented, with M11 review improvements underway. Migration `20261115_0011`
adds separate writing submissions. It has not been applied to protected databases.

| Check | Observed result |
| --- | --- |
| Current source migration head | `20261115_0011`, writing submissions; protected database revisions remain unverified |
| Main database revision | Unverified, read-only connection timed out |
| Existing isolated M08 database revision/counts | Unverified, read-only connection timed out |
| Application ports 3000/3008/3012 and API ports 8000/8008/8012 | Loopback connection unavailable |
| PostgreSQL 5432, Redis 6379, speech worker 8098 | Loopback connection unavailable |
| Ollama 11434 | Real local writing feedback passed schema validation; see latest regression record |
| Physical microphone acceptance | Pending in the inspected M09 report and PR description |
| Curriculum reviews | Five categories pending in inspected documentation, live records not queried successfully |
| New automated regression results | See the current checkpoint below and complete regression record |
| M10–M17 implementation | M10 implementation present with integration/build gates pending, M11 partial, M12–M17 pending |

See the [inventory and execution checkpoints](../roadmap/FLUENTLOOP_FINAL_ROADMAP.md)
and [manual acceptance procedure](FINAL_MANUAL_TESTING.md).

## Regression commands for the available baseline

Run only once dependencies and disposable services are ready. These commands are
reproduction instructions and do not imply a new passing result.

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py tests
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py --coach
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py
Push-Location frontend
npm run lint
npm run typecheck
npm run build
Pop-Location
```

The browser runners also build the frontend and reserve ports 3012/8012. Run them
sequentially. Check the current runner's fixture and ignored local configuration
before use. Do not run default Alembic upgrade commands against protected databases.

## Evidence required for final completion

Keep backend counts, frontend checks, Playwright counts and environment-gated skips
distinct. Record migration upgrade, data-preserving rollback, backup restore,
cross-user isolation and publication-denial checks in disposable PostgreSQL. Record
actual local Ollama, ASR and Piper results separately from mocked tests. Include
human microphone and screen-reader outcomes. Security and legal readiness require
their own review evidence. Measure performance before specifying production sizing.

Technical completion and public launch remain pending. Deployment, hosting purchases,
DNS changes, persistent database writes, content publication, commit and push have
separate authorization checkpoints in the master request.

## M10 implementation checkpoint on 2026-11-15

The owner explicitly deferred human microphone/browser/accessibility acceptance to
the final consolidated session. These checks no longer gate development. Current
implementation and verification details are in
[COMPLETE_REGRESSION_RESULTS.md](COMPLETE_REGRESSION_RESULTS.md).

Implemented grammar/listening catalog and sessions, saved history, bounded skill
evidence, Learn navigation, shared session/results labels and Progress integration.
Existing M07 recommendations consume saved assessment mistakes. This is a partial
M10 implementation. Vocabulary, reading, writing and broader analytics are pending.
M11–M17 have not been implemented in this checkpoint.

The initial continuation instruction below is superseded by the latest checkpoint.

> Continue on codex/remaining-project-readiness. Preserve all uncommitted files.
> Read the assessment design and regression results. Complete M10 vocabulary and
> original reading tasks using explicit learning-objective skill metadata and the
> existing grader. Add separate original writing submissions and validated advisory
> feedback with disposable migration tests if needed. Restore disposable PostgreSQL,
> Redis and speech tests where safe. Finish M10 automated verification, then proceed
> sequentially through M11–M17 preparation. Defer human acceptance to the end.
> Do not commit, push, publish, migrate protected databases or deploy.

## Latest continuation checkpoint

Vocabulary assessments, original reading context and original writing submissions
are implemented. The frontend provides all five categories, writing history,
feedback retry and revisions. Progress includes writing counts and actual unresolved
question recommendations. Existing objective grading and M07 mistake planning are
reused. The source pack contains three separate immutable draft lessons.

Writing migration `20261115_0011` passed a disposable SQLite operations test, including
empty rollback and refusal of populated rollback. A PostgreSQL integration case was
added but skipped because the dedicated service is unavailable. Existing migration
preservation tests now target explicit revision names.

M11 changes include six-level review queue support, objective skill/identity in
packet digests, skill-aware task validation and exercise relationship checks.
The draft authoring schema supports exactly A1–C2. Only original A1 content was
authored. Five independent review categories remain pending. Full staff editing,
version comparison and wider curriculum development remain unfinished.

Latest backend results are 265 passed and 10 skipped, followed by focused
frozen-passage/retry checks. Assessment/Tutor Playwright passed 11 cases. ESLint,
TypeScript and webpack production build passed. Real local Ollama feedback, speech
decoder tests and a Piper-to-Faster-Whisper Base synthetic pipeline passed. See the
[complete regression record](COMPLETE_REGRESSION_RESULTS.md) for exact evidence.

The default Turbopack build remains failed. Its CSS evaluation worker exits before
connecting. The cause is unresolved after testing the installed Node executable
and PATH explicitly. Docker is stopped and PostgreSQL/Redis integration, demo
startup and recovery remain blocked. The demo preflight correctly refused startup.

Resume with this instruction.

> Continue on codex/remaining-project-readiness and preserve all uncommitted work.
> Vocabulary, reading and writing are implemented. Read the latest regression
> record before repeating checks. Restore dedicated disposable PostgreSQL/Redis
> testing safely and diagnose the default Turbopack worker failure. Verify the M10
> demo and migration/concurrency/recovery checks. Complete independent M11 staff
> authoring/version comparison and curriculum integrity work, then continue through
> M12–M17 preparation. Keep final human acceptance deferred. Do not commit, push,
> merge, publish, migrate protected databases or deploy.
