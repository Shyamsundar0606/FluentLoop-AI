# Security and privacy readiness checkpoint

RC follow-up: the erasure replay rehearsal passed against a private pre-erasure
PostgreSQL snapshot, including interrupted audio cleanup and another user's data.
The real Mailpit expiration/reset/rate-limit flows passed. Broad axe WCAG2.2AA
checks found and verified fixes for muted-text contrast and link decoration.
Container/security rescanning is interrupted by the infrastructure incident in the
[RC checklist](../verification/RELEASE_CANDIDATE_CHECKLIST.md); the prior clean
dependency scans are dated evidence, not a new post-incident scan or launch approval.

Recorded 2026-11-15. This is technical preparation, not a legal compliance finding
or public launch approval. No protected database was changed.

## Controls inspected and tested

Passwords use Argon2id; opaque authentication/reset tokens are stored as hashes.
The application uses server-side sessions rather than a browser-stored JWT.
Production settings require secure cookies, explicit CORS origins and positive
token lifetimes. Mutating assessment, writing and authoring routes require CSRF;
their inference/creation endpoints have rate limits. Curriculum writes require an
active verified development-preview administrator. Review permission alone does
not grant draft editing. Packet digests bind reviews to current content versions.

The backend regression tests cover authentication, owner isolation, CSRF, rate
limits, draft denial and private inference context. The real M10 browser check
also observed ordinary learner draft denial and another user's writing returning
404. Answer keys remain server-side; only authorized content reviewers can view
them. These checks do not substitute for penetration testing.

Assessment text, learner answers and model output remain untrusted input. The
existing tutor does not expose database, shell or filesystem tools to Ollama.
Advisory writing feedback is schema validated, remains separate from the original
submission and never becomes an objective grade or CEFR certification. Existing
prompt-injection, retrieval-authorization and failure tests remain in the suite.

## Dependency audit results

### Current remediation

The earlier findings below are historical. Current `npm audit` reports zero
vulnerabilities. A scoped override upgrades only TypeScript ESLint's minimatch to
11.0.1, preserving unrelated older minimatch APIs. The installed consumer uses the
named `minimatch` API. The patched package supports Node 20. Lint, type checking,
both builds and 17 targeted browser checks passed after this change.

The actual updated `.venv-speech` environment was rescanned: 74 dependencies,
zero known advisory entries and no skipped packages. Targeted pins are FastAPI
0.133.1, Starlette 1.3.1, python-dotenv 1.2.2, dnspython 2.9.2 and pytest 9.0.3.
Pip was upgraded to 26.2 in both local environments; the production API Dockerfile
also pins its installer. Pydantic and the remaining application/speech pins were
preserved. Forty-eight compatibility tests and the complete 306-test suite passed
in a private candidate package directory before adopting the pins. The actual
installed-environment final regression is recorded in the current checkpoint.

FastAPI's [release notes](https://fastapi.tiangolo.com/release-notes/#01330)
document Starlette 1.x support from 0.133.0. Starlette's
[release notes](https://www.starlette.io/release-notes/#131-june-12-2026)
document the 1.3.1 form-parser limit fixes. Speech multipart handling makes these
server fixes relevant. Dotenv reads operator configuration; dnspython is an email
validation dependency. Pytest and pip findings affect test/install tooling. These
were remediated rather than dismissed as unused. A clean dated advisory scan does
not establish absence of security defects or legal compliance.

### Historical baseline findings

The audit ran against the local lockfile and installed speech/backend environment.
Reports are ignored private files under `.publication-private/integration-wsl/`.
Do not confuse a direct-pin scan with the complete installed-environment scan.

| Scan | Observed result |
| --- | --- |
| `npm audit --json` | Seven moderate findings; zero high/critical. The root advisory is minimatch globparts amplification, GHSA-g3hv-75wg-m249, propagated through TypeScript ESLint tooling |
| `npm audit fix --dry-run --json` | Proposed compatible tooling updates, but exited 1 with unresolved findings; no changes applied |
| `pip-audit -r requirements-speech.txt --disable-pip --no-deps` | Only six directly parsed pins scanned, no findings; incomplete coverage |
| `pip-audit --path .venv-speech/Lib/site-packages` | 31 advisory entries across five packages, including duplicate aliases: dnspython 2.9.1, pip 25.0.1, pytest 8.3.2, python-dotenv 1.0.1, Starlette 0.37.2 |

The original installed-environment findings were launch blockers. Audit output
lists fixes for dnspython from 2.9.2, python-dotenv from 1.2.2, pytest from 9.0.3
and pip through 26.2. Starlette advisories span several versions through 1.3.1;
the currently pinned FastAPI 0.111.1 constrains compatible Starlette versions.
Prepare a coordinated framework upgrade in a disposable environment, resolve all
advisories, then rerun auth, multipart limits, CSRF, speech, backend, browser and
build checks. Do not force an incompatible Starlette override into production.
Requery advisories when remediation begins; the report is a dated observation.

## Data inventory and retention gaps

| Data | Current behavior | Work needed before public use |
| --- | --- | --- |
| Profile, email and preferences | Account-owned relational records | Define lawful basis, operator identity, retention and rights procedure |
| Learning attempts, frozen exercises and writing revisions | Persisted history; revisions preserve originals; owned data removed by explicit permanent deletion; export excludes private snapshots | Verify backup erasure reconciliation and final retention disclosures |
| AI conversations and corrections | Owner-protected persisted history | Publish retention period and configured inference processor/location |
| Input microphone audio | Uploaded only on submission; replay saving is optional | Verify real-device consent/recording UX during final acceptance |
| Saved/generated audio | Private owner-checked playback; access expires within configured TTL, at most 24 hours; cleanup can lag | Monitor cleanup failures and backlog; document backup exclusions |
| XP and achievements | Explicit sync; opt-out retains history; included in owner export and permanent deletion | Final retention/disclosure review |
| Backups and logs | Operator-managed | Encryption, restricted access, expiry, restore procedure and redaction review |

Deactivation sets the account inactive and revokes sessions; it retains history.
Settings separately offers authenticated, CSRF-protected, password-confirmed export
and permanent deletion. Export has an explicit field allowlist, 100-row pages and
a 1.5 MB page budget; credentials, curriculum snapshots/keys and audio storage paths
are excluded. Responses use no-store and requests are rate limited and size bounded.

Deletion additionally requires the literal confirmation `DELETE MY ACCOUNT`.
The relational transaction removes owned account/learning/writing/conversation/
reward data and records a file-erasure outbox. Other users and authored curriculum
are preserved; staff revision attribution becomes null while restricted review
history remains. Audio playback immediately loses its authenticated owner; physical
files are removed in bounded retry batches (up to 100 keys per job, 20 jobs/pass).
Failed storage cleanup retains the job for the existing minute-based sweep.
Completed jobs clear storage keys and retain a restricted account UUID reference,
receipt and timestamps for 90 days after cleanup, then the sweep removes them.
Pending jobs remain until cleanup succeeds. There is no email, credential or
conversation text in this audit record. No real account was deleted during development.

Operator backups and restricted curriculum review/audit records are retention
exceptions disclosed before deletion. Backups must expire within 90 days to match
the reconciliation window. Before exposing a restored database, operators must
reapply subsequent erasure decisions using the restricted account references from
the current ledger, verify file cleanup and then authorize access. Do not restore
an older backup outside this window into public service. Reconciliation rehearsal,
public retention disclosures and operator rights-request review remain launch
gates; do not claim GDPR compliance from these technical controls.

Review [speech privacy](speech-data-privacy.md) and
[M09 privacy](MILESTONE_09_PRIVACY_AND_SAFETY.md) for existing worker and transcript
details. Age bands do not establish legal eligibility or parental consent.

## Performance evidence and remaining measurements

The production M10 browser journey completed in 29.5 seconds, including four
objective categories, real listening synthesis and one real Ollama writing-feedback
request. This is one synthetic end-to-end run, not endpoint latency or throughput.
No p95 latency, concurrent inference capacity, peak RAM/VRAM or multi-user load
result is established. Do not derive production capacity from pytest duration.

Before sizing hosting, benchmark login and catalog/learning endpoints against a
disposable database, then separately measure ASR, TTS and Ollama cold/warm latency,
queue saturation, memory and timeout recovery. Use fictional input and redact
request bodies. Set explicit release thresholds before accepting results.
