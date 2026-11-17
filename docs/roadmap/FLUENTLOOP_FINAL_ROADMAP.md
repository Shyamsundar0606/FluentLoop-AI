> Latest checkpoint (2026-11-15): [current implementation and verification](../verification/CURRENT_DEVELOPMENT_CHECKPOINT.md).
> Disposable PostgreSQL/Redis and default Turbopack are now working. The older
> checkpoint descriptions below are historical and are superseded by that record.

# Remaining project implementation inventory

Audited 2026-11-15 against merged M09 commit `fd6198b8ee34d123df90b3e35b6e6d83d6d6666a`.
This inventory describes inspected source, all five M10 category implementations
and the first M11 authoring/review improvements.
It does not certify completion of M10 through M17.

## Baseline and acceptance gates

PR #3 merged on 2026-11-11. Its head was `d66c9e2`. The merge commit's push
[CI run](https://github.com/Shyamsundar0606/FluentLoop-AI/actions/runs/43113085028)
completed successfully. The repository was clean on `main` at audit start.
Preparation is isolated on `codex/remaining-project-readiness`.

The updated owner request defers physical microphone, manual browser and human
accessibility acceptance to one final consolidated session. These pending checks
do not block local implementation. Record actual operator results at final acceptance.

Read-only connection attempts to main and isolated M08 timed out. Their current
database revisions and curriculum counts are unverified. Earlier reports are
historical evidence only. Code has one migration head, `20261108_0010`.

Loopback TCP checks found only Ollama on port 11434. Ports 3000, 3008, 3012,
8000, 8008, 8012, 5432, 6379 and 8098 were unreachable. A listening Ollama port
does not establish that a model can generate a response.

## Existing implementation and remaining work

| Milestone | Inspected implementation to reuse | Remaining implementation or verification |
| --- | --- | --- |
| M01–M02 | FastAPI auth and user routes, profile and onboarding, password reset, Next.js protected pages | Refresh end-to-end email and session verification when disposable services are available |
| M03–M04 | Curriculum models and importers, frozen session exercises, grading service, attempt idempotency and lesson progress | Preserve historical keys and snapshots in every subsequent migration |
| M05–M06 | AI orchestrator, curriculum retrieval, bounded exercise definitions, speech orchestrator, ASR and Piper providers, pronunciation practice | Physical microphone acceptance and refreshed real service checks |
| M07 | Daily plans, review cards and review attempts, scheduler, activity completion | Add assessment evidence through the existing planner without a second scheduler |
| M08 | Grammar library, focused practice, mistake review, content-review routes, version and packet digest checks | Five genuine independent reviews and a separately authorized publication decision |
| M09 | Scenario options, authored openers, saved corrections, completion summaries, shared voice transcript | Document physical microphone and audible playback acceptance |
| M10 | Five category interfaces, vocabulary/reading drafts, unscored writing and advisory feedback, paginated history, bounded skill evidence, existing grader and planner integration | Real PostgreSQL migration/concurrency/recovery, disposable demo verification, live browser integration and default Turbopack fix |
| M11 | Six-level draft authoring validation and review queue, skill-aware packet checks, objective/grammar relationship validation, immutable draft importer | Complete staff editing/version comparison workflow, expanded learning paths, broader draft coverage and verification |
| M12 | Existing recorded learning events and completion timestamps | Idempotent reward ledger, timezone-aware streak calculation, achievements and opt-out preferences |
| M13 | Existing scenarios, correction timing, voice recovery, pronunciation target practice | Audit missing scenarios, strengthen advisory feedback distinctions and test actual local inference failures |
| M14 | Existing five-item navigation and responsive components | Full account export/deletion design, account retention controls, responsive and keyboard audit, manual screen-reader acceptance |
| M15 | Existing RBAC, CSRF, rate limiting, upload validation, draft access controls, speech retention | Fresh security and dependency audit, measured load/inference/resource tests, privacy review and operational templates |
| M16 | Pytest, PostgreSQL integration suites and Playwright suites | Full integrated learner journey, disposable backup/restore rehearsal, regression and human acceptance evidence |
| M17 preparation | Docker configuration and existing local environment setup | Workload-based hosting selection, current pricing research, launch and operations runbooks, explicit launch approvals |

## Sequential implementation checkpoints

1. Preserve the current preparation and implementation branch. Restore disposable
   PostgreSQL, Redis, speech and inference readiness where safe. Record unavailable
   dependencies and continue independent implementation. Keep manual checks pending.
2. Continue the [assessment design](../architecture/MILESTONE_10_ASSESSMENT_DESIGN.md)
   on `codex/remaining-project-readiness`. Preserve all uncommitted work. Keep
   milestone changes separately auditable and obtain authorization before commits.
3. Validate M10 migrations and recovery in disposable PostgreSQL. Run complete
   backend tests, frontend lint, type checking, production build and Playwright.
4. Implement M11 through M16 in separate auditable branches or approved commits.
   Dependent phases require their preceding functionality and tests. Independent
   architecture and acceptance preparation may continue while gates are pending.
5. Prepare M17 hosting and operations using measured workloads and current provider
   pricing. Execute protected operations only with their specific authorization.

## Required approval evidence

Commit and push require explicit authorization for the prepared changes. Persistent
migrations require a verified recoverable backup and explicit target authorization.
Curriculum publication requires exact-version independent reviews and publication
authorization. Physical microphone and screen-reader acceptance require actual human
testing. Hosting purchases, DNS changes and deployment require separate approval.

The five curriculum review categories remain pending in the inspected review-status
document. Confirm live review records when database access returns. Avoid generating
approval records from this inventory.

## Current continuation boundary

The final consolidated human acceptance remains deferred. M10 implementation is
present but has unresolved integration/build gates. M11 has partial improvements.
M12–M17 remain pending. Continue with disposable database recovery and default-build
diagnosis while completing independent M11 authoring work, then proceed sequentially.
Preserve the current branch and uncommitted work.
