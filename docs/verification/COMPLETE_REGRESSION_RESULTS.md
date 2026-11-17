> Latest checkpoint (2026-11-15): [current implementation and verification](CURRENT_DEVELOPMENT_CHECKPOINT.md).
> Disposable PostgreSQL/Redis and default Turbopack are now working. The older
> checkpoint descriptions below are historical and are superseded by that record.

# Remaining milestones regression record

## RC verification results and incident

Actual new evidence: existing mail-backed auth browser suite4 passed (7.4s),
mail expiration/reset/rate-limit test1 passed (2.8s), erasure replay1 passed (8.72s),
66 WCAG2.2AA route/viewport audits passed after two confirmed fixes (1.3min), full
backend307 passed without skips (331.86s), explicit M09 upgrade/rollback1 passed
(10.74s). The bounded workload completed with zero unexpected errors. Three Linux
application images built; fresh container DB/Redis health and migrations passed.
Full container runtime/HTTPS/restart checks did not complete: C: exhaustion during
the optional image pull forced WSL emergency read-only mode. See the
[exact checklist and recovery gate](RELEASE_CANDIDATE_CHECKLIST.md). No recovery
success or production readiness is claimed.

## Latest adopted-runtime continuation

See the [current detailed results](CURRENT_DEVELOPMENT_CHECKPOINT.md#latest-continuation-curriculum-privacy-and-dependency-remediation).
The complete adopted-runtime suite passed 306 tests with no skips and one dependency
warning (306.24s); final privacy/curriculum checks through 0016 passed 20 (62.02s).
The combined mocked browser suite passed 17 (44.7s); the Settings axe/privacy check
passed separately (7.1s); the current real assessment browser passed one (25.5s).
Real Piper-to-Faster-Whisper Base passed on synthetic audio (5.56s). Fresh backup
restore verified all 65 public tables through 0016. Lint/types and default/webpack/
standalone builds passed; Compose static validation and standalone HTTP smoke passed.
Actual installed Python and npm advisory scans are clean at this checkpoint.
Scope limitations and failed initial probes are recorded in the detailed checkpoint;
mail-backed complete E2E and container/HTTPS/load verification are not claimed.

## M10 remaining skills and M11 review checkpoint on 2026-11-15

| Verification | Actual result |
| --- | --- |
| Final complete backend run | 265 passed, 10 skipped, 2 dependency warnings, 184.55 seconds |
| Focused assessments, review and audit regression | 15 passed, 24.46 seconds |
| Follow-up frozen-passage and writing-retry checks | 8 passed, 16.97 seconds |
| Assessment and existing Tutor Playwright | 11 passed, 33.7 seconds, APIs mocked |
| Final ESLint and TypeScript | Passed |
| Explicit webpack production build | Passed, 39 pages, writing route included |
| Default Turbopack build | Reproduced failure creating the CSS evaluation worker |
| Real Ollama writing feedback | `llama3.2:3b`, production provider and feedback schema, validated output, 12.5 seconds |
| Optional speech decoder suite | 4 passed, 3.27 seconds in `.venv-speech` |
| Real Piper and Faster-Whisper Base | 176684-byte in-memory WAV, French nonempty transcript, `transcribed`, 13.16 seconds |
| Assessment demo startup preflight | Correctly refused startup while PostgreSQL/Redis were unavailable |

The complete backend run's ten skips are nine PostgreSQL cases and the speech
decoder module missing NumPy in `.venv312`. The separate optional speech environment
passed the decoder tests. PostgreSQL remains unverified. The new integration case
covers writing migration, frozen reading context and refusal of lossy downgrade.
Existing PostgreSQL preservation tests now target named revisions rather than a
number of relative downgrades, so subsequent migrations do not shift their baseline.

The writing migration was exercised with Alembic operations in disposable SQLite.
Empty rollback succeeded and populated rollback was refused. This does not establish
PostgreSQL migration safety. Frozen reading context survives later source changes.
Writing idempotency survives a saved-level change while access remains authorized.

The new original source pack imports three draft lessons and seven objective
exercises using existing helper functions and lexical records. Repeat imports are
idempotent and same-version source edits are rejected. Real protected databases
were not imported into or migrated. Human reviews remain pending.

Review queue and packet validation support all six levels. Packets include objective
skill/identity and grammar identity, validate exercise relationships, and handle
reading/writing task requirements. Packet digests therefore change relative to the
older representation. Existing review history remains stored and only exact current
packet decisions apply. Tests demonstrate structural level support, not educational
approval or equivalent content coverage across levels.

Turbopack failed before compiling application endpoints, while its CSS loader's
Node process exited with code 0 before connecting. The failure reproduced with
Node 24.17.0 using the installed executable explicitly and with that directory
first on PATH. The project loader configuration matches its installed package's
usage instructions. The precise underlying cause remains unresolved. Webpack
success is reported separately. No tests or default build configuration were disabled.

Docker's Linux-engine pipe was absent and no local PostgreSQL/Redis service was
available. The new demo preflight checks those dependencies before creating a
database or running a build. End-to-end startup remains pending. Real AI/speech
checks above used fictional and synthetic input without persistent learner records.

M10 is not fully verified. M11 is partial. M12–M17 preparation remains pending.

## M10 first slice on 2026-11-15

This record covers grammar/listening assessments and their frontend integration.
It does not mark M10 complete or cover unimplemented M11–M17 features.

| Verification | Actual result |
| --- | --- |
| Full backend run, before final additional test | 256 passed, 9 skipped, 2 dependency deprecation warnings, 177.11 seconds |
| Focused assessment API run, including additional test | 4 passed, 2 dependency deprecation warnings, 7.81 seconds |
| New assessment Playwright | 4 passed, 8.1 seconds, all APIs mocked |
| Existing mocked AI Tutor Playwright | 6 passed in the combined run; that run also exposed locator ambiguity in two new tests, subsequently fixed and rerun |
| Final ESLint and TypeScript | Passed, including the added browser fixtures |
| Production build using `next build --webpack` | Passed, including 38 generated pages and the assessment route |
| Default Turbopack production build | Failed on Google Fonts fetch in the restricted process, then failed launching its CSS worker outside that process |
| Real PostgreSQL/Redis, migration and recovery tests | Pending, Docker engine stopped and services unavailable |
| Real Ollama/Faster-Whisper/Piper | Not executed for this slice |
| Physical microphone and human screen reader | Pending final consolidated acceptance |

The full backend skips cover one speech decoder module missing NumPy and eight
PostgreSQL integration cases without their dedicated database configuration. These
are explicit gaps. Existing tests were retained. The existing Learn tab assertion
now expects four entries and explicitly checks the new Assessments destination.

API coverage uses the actual in-memory SQLAlchemy models and grader. It verifies
catalog confidentiality, saved level filtering, duplicate starts, duplicate answers,
idempotent completion, history, score evidence, separate lesson progress, draft
denial after permission loss, authentication, cross-user denial, CSRF, rate limits
and mistake evidence consumed by the existing planner.

Browser coverage includes 320px layout, keyboard activation, failed start recovery,
catalog failure announcements, ordinary learner empty state, question rendering,
answer submission, reload persistence and return to assessments. Browser mocks
verify frontend behavior. They do not establish backend integration or actual audio.

The first restricted API test attempts stalled while Python created its event-loop
socket pair. They were interrupted and rerun outside that restriction with disposable
fixtures. The first browser attempt used a frontend with a mismatched API URL and
redirected to sign-in. The isolated frontend was restarted with the explicit mocked
API URL. No production configuration or test timeout was changed.

No database migration was added. History is paginated, and skill evidence uses a
declared window of at most 100 recent sessions. This is not all-time analytics or
an estimate of proficiency. The initial definition list still needs explicit
objective display and separate reading, vocabulary and writing policies.
