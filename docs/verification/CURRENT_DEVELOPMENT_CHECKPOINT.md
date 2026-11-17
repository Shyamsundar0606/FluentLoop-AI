# Current development checkpoint

## RC verification and recovery checkpoint

**Read first:** [release-candidate checklist](RELEASE_CANDIDATE_CHECKLIST.md).
Mail-backed E2E, erasure-replay,66 WCAG2.2AA route/viewport checks and the bounded
five-client workload passed. Full backend307 passed; explicit M09 upgrade/rollback
preservation passed separately. Three Linux application images built and the fresh
container database migrated through0016.

Container validation is now blocked by an actual infrastructure incident: the
isolated Ollama image pull exhausted C:, and Ubuntu entered emergency read-only
mode with I/O errors. The pull and owned daemon/workloads were stopped. The
existing Docker Desktop environment was not started. Automatic approval review
rejected a read-write remount for filesystem-corruption risk; it was not executed
or bypassed. Backup-first Ubuntu recovery onto D: requires explicit owner approval;
the request is pending. Do not retry writes, repair, unregister/reset WSL or delete
volumes. Preserve all repository work and private data. The checklist has exact
evidence, remaining gates and safe continuation steps.

## Latest continuation: curriculum, privacy and dependency remediation

Updated 2026-11-15. This section supersedes the older implementation-boundary and
test tables below. Work remains on `codex/remaining-project-readiness`, uncommitted.
No protected database or real account was modified, and nothing was deployed,
published, committed or pushed.

Implemented in this continuation:

- Draft course metadata and per-version provenance editing. License/source changes
  create a separate source record, preserving earlier provenance. CEFR stays one
  of exactly A1–C2; reclassification uses a separate correctly classified draft
  release rather than changing shared live identities.
- Eight resource text editors: objectives, grammar topics/rules/examples,
  vocabulary senses, translations, French example sentences and conjugation forms.
  Only resources exclusively linked to the draft course can change. Shared,
  published, foreign or retired resources are rejected. Exercise direct references
  also participate in scope checks. IDs and historical packets remain stable.
- Ordered lesson prerequisites, validated against unique earlier lessons in the
  same course. Forward links, cross-course links and cycles are rejected in both
  edits and review validation. They are advisory curriculum metadata, not a new
  hard completion gate. Learner lesson detail exposes the authorized references.
- Password-confirmed, owner-scoped account export with explicit safe projections,
  100-record pages, a 1.5 MB page budget, CSRF, rate limiting and request limits.
  Settings downloads private JSON pages. Credentials, curriculum snapshots/keys,
  internal model metadata and audio storage paths are excluded.
- Explicit permanent deletion distinct from deactivation. It requires the current
  password and `DELETE MY ACCOUNT`, removes owned relational data transactionally,
  clears session cookies and preserves other accounts and authored curriculum.
  A durable outbox retries private-file cleanup. Restricted UUID reconciliation
  receipts expire 90 days after cleanup; pending jobs remain until successful.
- Targeted dependency remediation: FastAPI0.133.1/Starlette1.3.1, dotenv1.2.2,
  dnspython2.9.2, pytest9.0.3 and local pip26.2. Other application/speech pins remain.
  A scoped minimatch11.0.1 override fixes the TypeScript ESLint advisory chain.
- Separate non-root production Dockerfiles, opt-in Next standalone output, Caddy
  reverse-proxy configuration and production Compose preparation without automatic
  migrations/imports. No container was launched from the production configuration.

New migrations are `20261115_0014` prerequisites, `0015` erasure outbox and `0016`
restricted backup-reconciliation references. Lossy downgrades are guarded. Only
fresh disposable databases were migrated; source head is now `20261115_0016`.

| Verification in this continuation | Actual result |
| --- | --- |
| Existing authoring/review regression after initial additions | Seven passed, 12.82 seconds |
| Expanded scoped-resource/provenance/prerequisite API tests | Fourteen passed, 20.59 seconds |
| AI/coach/speech/decoder plus PostgreSQL authoring selection | 77 passed, 39.50 seconds; initial selection typo corrected before execution |
| Initial privacy API tests | Three passed, 4.30 seconds |
| Real PostgreSQL account erasure | One passed, 10.49 seconds; initial synthetic writing fixture used a dictionary for a text column, corrected |
| Candidate patched-runtime compatibility | 48 passed, 34.27 seconds |
| Complete candidate-runtime suite | 306 passed, no skips, one dependency deprecation warning, 366.12 seconds |
| Complete actual adopted-environment suite | 306 passed, no skips, one dependency deprecation warning, 306.24 seconds; final reconciliation extension checked separately below |
| Final privacy/curriculum APIs, PostgreSQL and migration guards through0016 | Twenty passed, 62.02 seconds; includes empty supported downgrade, populated refusal, UUID retention expiry and storage retry |
| Combined mocked browser regression | Seventeen passed, 44.7 seconds |
| Settings automated WCAG2A/AA and WCAG2.1AA audit | One privacy/browser test passed, 7.1 seconds, including axe scan of the complete 320px Settings page with deletion controls expanded; no violations |
| Current real assessment browser with PostgreSQL, Piper and Ollama | One passed, 25.5 seconds; all five categories, persistence/resume, ordinary draft denial and cross-user denial |
| Real Piper to Faster-Whisper Base | 109,100-byte synthetic WAV; nonempty French, transcribed; 5.56 seconds |
| ESLint, TypeScript, default and webpack builds | Passed after privacy/resource/override changes; final added accessibility test typechecked in final checks |
| Opt-in standalone build and smoke | Passed, login and 46,270-byte CSS both HTTP200; stopped before rebuilding to release a Windows directory lock |
| Production Compose validation | `config --quiet` passed with inert values; no daemon start or deployment |
| Actual installed Python audit | 74 dependencies, zero advisory entries, no skipped packages |
| npm audit | Zero vulnerabilities after scoped override; still zero after adding pinned axe tooling |
| Fresh disposable backup/restore through0016 | 322,098-byte custom archive; all65 public tables matched row counts and ordered whole-row fingerprints; four sessions, eleven frozen exercises/attempts and one writing submission preserved |
| Final source checks | 92 changed/untracked text files scanned by Gitleaks with no findings; Python/JSON syntax, local Markdown links and `git diff --check` passed |

Changed-file groups in this continuation: curriculum authoring/resource services,
review packets/routes, lesson response schemas and prerequisites model; privacy
router/service/model and retention sweep; Alembic environment plus migrations0014–0016;
Settings/privacy/structured staff components; dependency manifest/lock and opt-in
Next output; three production/deploy configuration files plus the Caddyfile;
focused API/PostgreSQL/Playwright tests and these verification/security/operations
records. Earlier assessment, motivation and coach changes remain preserved.

Local sequential loopback timing samples used the fresh disposable demo. Profile:
25 requests, p50 11.04ms, p95 12.72ms. Assessment catalog: ten requests, p50 166.05ms,
p95 185.63ms. Password-confirmed profile export: three requests, p50 100.87ms,
p95 102.24ms. These small warm samples include client/network time and are not
production capacity or sustained-load evidence. No bottleneck threshold or hosting
size is inferred from them.

Remaining work before final technical/manual acceptance:

- Real email-backed registration/reset/onboarding journey with an isolated mail
  stack; the earlier two Mailpit-dependent tests are not claimed passed.
- Broader route-by-route axe, contrast, responsive, scenario/voice transition and
  concurrent-load coverage. Physical microphone and human screen reader remain
  deferred to the one consolidated final session.
- Rehearse restore-time replay of erasure references. Backup retention must not
  exceed the 90-day reconciliation window. Final public retention/legal/operator
  disclosures still need review.
- Linux production image/runtime, private service connectivity, volume permissions,
  HTTPS/certificate and monitoring validation in isolated staging. Docker engine
  remains stopped. Provider quotes, sizing, immutable image digests and production
  operations acceptance remain pending. No infrastructure purchase is authorized.
- Shared curriculum changes still require a separate versioned resource/release;
  wider educational coverage and all five genuine independent reviews remain
  separate from code completion and curriculum publication authorization.

Current continuation instruction:

> Preserve all uncommitted work on codex/remaining-project-readiness. Read this
> latest section first. M11 scoped editing and M14 account export/deletion now
> exist, source head is0016, and recorded npm/Python advisories are remediated.
> Reuse the guarded WSL service helper; do not rerun its one-time initializer.
> Finish the isolated mail-backed learner journey, broader accessibility/voice and
> load verification, backup erasure-reconciliation rehearsal and Linux production
> configuration checks. Update actual results without repeating completed work.
> Keep physical microphone/screen-reader acceptance deferred until the final
> consolidated session. Do not commit, push, merge, publish curriculum, deploy,
> delete real accounts or migrate protected databases.

The following sections preserve the preceding checkpoint and its historical evidence.

Handoff cleanup: demo, mock frontend, standalone smoke server, speech worker and
dedicated PostgreSQL/Redis are stopped; ports3012/3017/3018/8012/8098/55432/56379
were verified closed. The generated credential fixture was explicitly removed
after the tool-driven Ctrl+C stop left it behind. Databases and backups remain
retained. Normal demo startup instructions below create new temporary credentials.

Recorded 2026-11-15 on `codex/remaining-project-readiness`. All changes remain
uncommitted. This record supersedes earlier unavailable-service/build observations
in the regression, roadmap and final-verification documents. Historical results
remain in those documents. The project is not fully complete or launch ready.

## Infrastructure recovery and build investigation

Docker's engine was stopped. Starting the existing Compose backend would run
automatic migrations, so testing used fresh PostgreSQL 16.15 and Redis 7.0.15
processes in WSL Ubuntu-24.04. Signed Ubuntu packages were extracted into a private
user cache without installing system services. Both services require a random
private password and listen on loopback ports 55432 and 56379. PostgreSQL readiness
and authenticated Redis PING passed from Windows. No protected database, Docker
volume or saved main/older preview configuration was changed.

Integration tests create fresh databases and apply the current head there. The
ignored local state and helper scripts are in
`.publication-private/integration-wsl/`. They contain secrets and machine-specific
paths and must not be committed. The recovery is a verified local alternative,
not a portable replacement for the supported PostgreSQL/Redis stack.

The Turbopack CSS worker failure was reproduced. A temporary private Node worker
tracer observed a subsequent successful connection. Then uninstrumented warm and
cold-cache default builds succeeded, followed by further normal builds. The prior
cache was moved to a verified in-workspace private path, not deleted. No dependency
downgrade, test suppression, permanent preload or bundler configuration change was
made. The original trigger remains unconfirmed; generated worker/cache state is
a possibility, not a proven root cause. Default and webpack results are separate.

## Implemented functionality and boundaries

| Area | Current implementation | Remaining work |
| --- | --- | --- |
| M10 | All five assessment categories; frozen reading; objective grading; writing originals/revisions/history and advisory Ollama feedback; existing planner recommendations; live demo verification | Final consolidated human acceptance; broader email-backed full journey remains unverified in this session |
| M11 | Six-level validation and reviewer packets; draft JSON creation; draft sections, lesson details and exercise/key editing; persisted revision snapshots and comparison UI; stale-digest rejection; edit invalidates current approvals | Structured in-place editing for shared grammar tables, vocabulary, examples, objectives and prerequisites; complete six-level curriculum paths/content coverage; wider live authoring browser checks |
| M12 | Unique reward ledger, explicit sync, timezone calendar streaks, achievement history, dashboard, optional motivation in Settings | Broader reward-source/browser integration and final usability acceptance |
| M13 | Existing tutor/speech reused; four additional scenarios with vocabulary coaching and level filtering; synthetic speech/inference evidence | Wider contextual-correction and real voice-scenario regression; physical microphone acceptance deferred |
| M14 | Five destinations preserved; Settings retention explanation and motivation preference; tested keyboard/skip link and responsive widths | Full-page accessibility/contrast/screen-reader audit; export and permanent deletion implementation |
| M15 | Auth/owner/draft controls retained; real advisory scans and privacy/data inventory prepared | Resolve dependency advisories; implement rights/retention workflow; measure capacity and complete security review |
| M16 | Disposable PostgreSQL/Redis regression; real M10 browser; targeted browser checks; backup/restore rehearsal | Whole learner journey including mail stack; accessibility automation beyond targeted checks; load and final manual acceptance |
| M17 preparation | Launch architecture, environment separation, migrations/recovery, monitoring and incident runbook documented | Production images/proxy implementation and validation; pricing/sizing; staged launch rehearsal and separate authorization |

M11 snapshots start when explicitly persisted; no earlier history is fabricated.
Comparisons can show all packet fields actually captured, including answer keys
for authorized staff. Direct editing includes section text, lesson title/description/
study time, and existing exercise text, validated format data, listening text and
answer keys. Option IDs and exercise format remain stable; adding different choices
requires a new exercise. Existing versioned importers handle shared structured
grammar/vocabulary data. Packet option IDs are now part of review digests, so older
packet approvals cannot silently apply to the changed representation. Draft JSON
creation uses immutable release identifiers, does not overwrite an older release's
license metadata, and keeps content unpublished. The three original A1 drafts are
preserved. Genuine independent review remains pending in all five categories.

Reward sync runs only on an explicit CSRF-protected POST. GET does not award XP.
Published completed activities qualify; development-preview completions do not.
The source tuple is unique and concurrent PostgreSQL syncs serialize on the user.
The ledger stores original activity time and a calendar date computed in the
profile timezone at first sync. Later timezone edits do not rewrite awarded dates.
Opt-out preserves existing history; re-enabling allows explicit sync of qualifying
unrewarded activities. XP indicates activity, never language proficiency.

Source migrations are 0011 writing submissions, 0012 curriculum revisions and
0013 motivation. Each protects retained data during downgrade. Only disposable
databases were upgraded. Frozen exercises, keys, writing and prior review history
are preserved by the new editing/import workflows.

## Automated evidence

| Check | Actual result |
| --- | --- |
| Full backend before M12/M13 additions | 282 passed, no skips, two dependency deprecation warnings; 260.13 seconds |
| First full run with M12/M13 | 288 passed, two outdated scenario-count assertions failed; 320.34 seconds. Assertions updated for 27 total/five A1 scenarios with new ID and level checks |
| Complete backend rerun before structured editor extension | 290 passed, no skips, two dependency deprecation warnings; 339.01 seconds |
| Structured authoring focused backend | Seven passed, 11.54 seconds; failed edits leave no revision or partial content changes |
| Final authoring follow-up | Five passed, 8.12 seconds, including actual submission graded against the original frozen key after a current draft key edit |
| Structured key preservation in PostgreSQL | One passed, 7.42 seconds; frozen old key retained while current draft changes |
| Complete backend after structured extension | 292 passed, no skips, two dependency deprecation warnings; 277.56 seconds. Final key-grading assertion additionally passed in the five-test follow-up |
| Focused new scenario and motivation tests | Ten passed, 7.28 seconds |
| Final assessment/Tutor/authoring/reward/Settings Playwright | 15 passed, 33.1 seconds; mock API; keyboard and mobile coverage |
| Extended authoring Playwright | Two passed, 3.4 seconds, including structured stable-key submission; mock API |
| Mock account and shared learning flow | Three passed, 5.8 seconds |
| Extra mixed account browser batch | Three passed, two email-backed tests failed because API8001/Mailpit stack was unavailable; no application-failure conclusion |
| Real M10 browser against production frontend3012/API8012 | One passed, 29.5 seconds; real PostgreSQL, Ollama writing feedback and Piper listening |
| ESLint and TypeScript | Passed after final Settings changes |
| Default Turbopack production build | Passed after final Settings changes, 39 pages; prior uninstrumented cold-cache pass also recorded |
| Explicit webpack production build | Passed after final Settings changes, 39 pages |
| Backup/restore | Passed custom-format dump/restore of disposable demo; 310,549-byte archive; matched counts and ordered fingerprints for four sessions, eleven frozen exercises, eleven attempts and one writing submission |
| Dependency audit | Open advisories; see security report. No clean-security claim |
| Changed-source checks | Gitleaks scanned 69 changed/untracked text files, no leaks; Python/JSON syntax and local Markdown links passed; `git diff --check` passed |
| Physical microphone/screen reader | Pending final consolidated acceptance |

The live M10 test covers grammar, vocabulary, reading and listening assessments,
saved answers/results, frozen reading and reload/resume, writing feedback and
history, Progress, ordinary learner draft denial and cross-user writing404.
Confidential answer lookup is confined to trusted test-side disposable database
access; learner responses are checked for key leakage. This does not cover all
six exercise formats in a live browser; backend interactive tests exercise them.

Earlier real checks also passed the decoder suite and a Piper-to-Faster-Whisper
Base synthetic pipeline. They are distinct from physical microphone acceptance.
See [historical regression evidence](COMPLETE_REGRESSION_RESULTS.md).

## Local reproduction and final acceptance preparation

At handoff, the owned demo, mock frontend3017, speech worker8098 and dedicated
WSL PostgreSQL/Redis have been stopped. The private database cluster and backup
remain retained. URLs below require startup; they are not currently live.

These commands use the existing private machine state; do not copy credentials
into terminal output. Run from the project root. Inspect occupied ports first.
The private control helper refuses a wrong root/port/role or occupied startup port.
Its `start` action reuses the disposable cluster; do not rerun the one-time
`start.py` initializer against an existing data directory.

```powershell
wsl.exe -d Ubuntu-24.04 -- python3 '/mnt/d/shyam/Projects/FluentLoop AI/.publication-private/integration-wsl/control.py' start
.\.venv312\Scripts\python.exe .publication-private\integration-wsl\tests.py
.\.venv-speech\Scripts\python.exe backend\scripts\m08_local.py worker
```

Run the speech worker in its own terminal. Then start a fresh demo in another:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py serve --integration-state .publication-private\integration-wsl\state.json
```

After its readiness message, use [login](http://127.0.0.1:3012/login),
[assessments](http://127.0.0.1:3012/assessments),
[Home rewards](http://127.0.0.1:3012/dashboard) and
[Settings](http://127.0.0.1:3012/settings). These URLs work only while the demo runs.
It creates a fresh `fluentloop_m08_3_test_*` database and temporary accounts.
All curriculum remains draft; preview completion intentionally earns no XP.
Use automated published synthetic fixtures for reward verification, not publication
of real drafts merely to demonstrate rewards.

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py copy-email
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py copy-password
Set-Clipboard -Value ''
```

Paste each credential before copying the next. Ctrl+C stops the demo and its
children; stop the separately started worker in its terminal. The local service
control `stop` action stops only the validated disposable PostgreSQL/Redis. Retain
the private cluster and backup for explicit future cleanup. Do not stop unrelated
Ollama services. The testing frontend3017 uses mocks and is not a learner demo.

Complete the [single manual guide](FINAL_MANUAL_TESTING.md) only after remaining
technical work. Do not request intermediate screenshots or owner testing.

## Exact continuation

> Continue on codex/remaining-project-readiness; preserve all uncommitted work.
> Read CURRENT_DEVELOPMENT_CHECKPOINT.md and PRIVACY_AND_SECURITY_READINESS.md.
> Disposable WSL PostgreSQL/Redis and default Turbopack have been recovered.
> Reuse the guarded private control helper/state, never the one-time initializer.
> Finish M11 structured field editing and six-level curriculum integrity, expand
> M12/M13 integration coverage, then complete M14 export/deletion/accessibility.
> Resolve M15 dependency advisories with a compatible framework upgrade in a fresh
> disposable environment. Run the complete M16 learner journey with a real local
> mail stack, capacity/security checks and recovery. Implement and validate the
> M17 production preparation gaps listed in the launch runbook. Keep human
> microphone/screen-reader acceptance deferred to one final session. Do not commit,
> push, merge, deploy, publish curriculum or migrate protected databases.

Related: [security/privacy](../security/PRIVACY_AND_SECURITY_READINESS.md),
[launch preparation](../operations/LAUNCH_PREPARATION.md),
[assessment design](../architecture/MILESTONE_10_ASSESSMENT_DESIGN.md).
