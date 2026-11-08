# Milestone 08 final verification

## Scope

M08.4 adds content validation and the independent review queue, packet
inspection, listening and versioned decisions. M08.5 extends the existing
lesson reference and provides French accent insertion for written exercises.
M08.6 adds per-topic recent evidence and exact mistake retries. M08.7
batches the lesson library and grammar availability queries and verifies
keyboard and responsive behavior. M08.8 adds the current-review gate to
canonical publication and tests learner access through a disposable
publication simulation.

The implementation touches the existing FastAPI curriculum, learning,
publication and settings modules, the review service and API, the Profile
review workspace, lesson and practice components, and the disposable test
runner. It reuses the existing session engine, study planner, review
scheduler, speech worker and provenance schema. No new migration was added.

## Local startup and tests

Run these commands from the project root in PowerShell with the existing
local PostgreSQL, Redis and speech worker available:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
.\.venv312\Scripts\python.exe backend\scripts\m08_final_audit.py
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py tests
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py
Push-Location frontend
npm run lint
npm run typecheck
Pop-Location
```

The browser runner creates a disposable M08 database, migrates it to
`20261104_0009`, imports the three draft courses and builds the frontend.
It runs on `http://127.0.0.1:3012` and
`http://127.0.0.1:8012/api/v1` during verification. It stops its own frontend
and API afterward. The fixture creates an admin, learner and separately
granted reviewer. The reviewer test records a synthetic correction.

The persistent demo at `http://127.0.0.1:3008` and its API at
`http://127.0.0.1:8008/api/v1` were used for read-only checks. The review
workspace needs the final backend code and, for decision entry, an explicit
reviewer grant. Keep persistent database operations outside the disposable
test commands. The [M08.3 guide](MILESTONE_08_3_VERIFICATION.md) describes
the existing demo and its proven backup procedure.

## Accessibility, performance and recovery

The browser suite exercises keyboard activation of topic practice,
accent insertion at the caret, native audio controls, audio retry, lesson
resume and saved results. The responsive check uses 320, 390, 768, 1024 and
1440 CSS pixel widths. The app retains its existing focus styling and
reduced-motion preferences. A manual screen-reader and contrast audit is
pending. This is a targeted check against [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

The read-only local measurement counted five SQL statements to project 23
lessons. The grammar projection for 13 topics dropped from 243 SQL statements
and 544 ms to eight statements and 55 ms in separate local samples. The count
excludes loading the signed-in identity and preferences. The grammar projection
uses the most recent 200 attempt rows. Production load testing and detailed
navigation and audio latency budgets remain open.

The automated checks exercise loss of an answer response, duplicate
submission, listening retry, stale decisions and refresh. Existing
provider failure tests and real inference checks serve different purposes.
A deliberate live PostgreSQL or external provider outage was outside the
scope of the read-only demo check.

## Curriculum and publication

The read-only audit found 23 draft lessons and 81 exercises across the
three A1 courses, with zero published lessons. All five independent review
categories are pending. A2 through C2 have proposed coverage in the
blueprint. The feature branches, deployed services and persistent curriculum
were outside the write scope.

A fresh 353,063-byte custom PostgreSQL backup was restored into a separate
temporary database. All 59 restored table fingerprints matched the source
snapshot, and a second read showed zero changed source tables. The private
backup remains available and the temporary restore database was removed.

## Verification results

The final complete backend suite passed **262 tests**, including disposable
PostgreSQL checks, with two dependency deprecation warnings. The final
focused backend run passed **38 tests**. The production-build Playwright
suite passed **seven tests** against the final optimized projections.

ESLint, TypeScript, the production build and the redacted secret scan passed.
Live smoke checks reached PostgreSQL at revision `20261104_0009`, Redis
`PING`, FastAPI readiness and the Next.js login page. Ollama returned a real
completed inference. Faster-Whisper Base recognized the expected phrase in a
synthetic French recording. Piper generated a 22,050 Hz WAV.

The disposable publication journey checks registration, email verification,
level selection, a daily plan, draft denial before approval, canonical
publication with explicitly synthetic approvals, a saved lesson, grammar
practice, mistake resolution, tutor and speaking entry points, and ownership
denial from a second learner account. The authenticated browser suite
exercises the preview journey on PostgreSQL, including all six formats,
lesson and topic navigation, sign-out and sign-in persistence, listening
recovery, and a versioned reviewer decision. Manual testing of the final
code with personal browser profiles and real reviewer identities is pending.

- [Content audit](../content/MILESTONE_08_CONTENT_AUDIT.md)
- [Independent review status](../content/MILESTONE_08_INDEPENDENT_REVIEW_STATUS.md)
- [Learning architecture](../architecture/MILESTONE_08_LEARNING_ARCHITECTURE.md)
- [Release readiness and remaining blockers](MILESTONE_08_RELEASE_READINESS.md)
