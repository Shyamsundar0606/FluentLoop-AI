# Release-candidate verification status

Recorded 2026-11-15. **Public launch blocked; technical verification incomplete.**
All repository work remains uncommitted on `codex/remaining-project-readiness`.

## Current infrastructure incident

An isolated Docker daemon was created in a new WSL user-cache directory, using its
own Unix socket, data root and client configuration. Docker Desktop and its existing
volumes were not started or modified. The production API, frontend and speech images
built successfully, and fresh container PostgreSQL/Redis/Mailpit started. Missing
private iptables tooling initially prevented embedded DNS; extracting tools into
the private daemon directory resolved DNS, and the test database migrated to0016.

The large Ollama image pull then exhausted host C: space as the WSL virtual disk
grew. The WSL root entered emergency read-only mode; reads of some files returned
I/O errors. The pull was interrupted and the task-owned daemon was sent SIGTERM.
Owned Windows demo, speech and Mailpit processes were stopped. About72 MB of C:
space was subsequently available, which does **not** establish filesystem recovery.
D: had about278 GB free. No further image downloads or root-filesystem writes
should be attempted before recovery. The stopped private daemon's images, volumes
and incomplete download remain retained; removal of its incomplete download was
refused by the read-only filesystem.

Automatic approval review rejected a read-write root remount because of filesystem
corruption risk and authorization limited to cache cleanup. It was not executed.
No workaround, forced filesystem repair, WSL unregister/reset or protected-volume
deletion was performed. Backup-first Ubuntu recovery to D: requires explicit owner
authorization. An approval request is pending. Preserve existing Ubuntu contents
and all private test volumes. Future container storage must be placed on D: with
a checked free-space budget before resuming large image work.

## Evidence and gates

| Area | Implemented / automated evidence | Remaining gate |
| --- | --- | --- |
| Mail lifecycle | Existing auth browser suite4 passed (7.4s); additional real Mailpit link/reset/rate-limit test1 passed (2.8s) | Final human email/browser walkthrough |
| Mail cases | Delivery, verification/activation, expired/consumed/unknown/malformed tokens, password-reset delivery/expiry/success, duplicate registration409 and enforced429/Retry-After | No real email was sent; capture-only loopback SMTP |
| Privacy reconciliation | PostgreSQL pre-erasure snapshot replay test1 passed (8.72s); interrupted cleanup, two writing records, learning/assessment evidence, AI/voice metadata, achievements/export and another user's preservation | Operator authorization and restricted-ledger handling on any real restore |
| Accessibility | Confirmed muted-text contrast and link-decoration defects fixed; 66 real route/viewport axe WCAG2.2AA checks passed in1.3min; keyboard skip/focus and reduced-motion assertions passed | Manual screen reader/hardware; automation is not certification |
| Load | Five concurrent clients,100 read requests across five endpoints,50 Redis pings; zero unexpected errors; all read p95 below predeclared2000ms | Sustained production workload, hardware sizing and hosting selection |
| Inference | Two concurrent real tutor requests succeeded; real Piper and Base transcription succeeded in controlled workload | Container inference and final physical microphone acceptance |
| Backend | Full suite307 passed, no skips, one dependency warning (331.86s) | New baseline test verified separately below |
| M09 migration baseline | One explicit M09-to-head, supported empty-feature downgrade and re-upgrade test passed (10.74s); whole-row history fingerprints unchanged | Future protected migration remains separately authorized |
| Containers | Three production application images built; private DB/Redis healthy; complete migration chain ran in container | Runtime/HTTPS/cookie/CORS/restart/isolation validation interrupted by disk incident |
| HTTPS | Local-only Caddy test configuration prepared | Certificate and proxy checks not yet completed; no public certificate claim |
| Backups | Previous custom-format backup/restore matched65 public tables through0016; additional independent template-snapshot erasure replay passed | Repeat final combined rehearsal after infrastructure recovery |
| Security | Earlier actual Python74-package and npm scans clean; secret/static checks rerun at handoff | Final rescans/container scanning after recovery |
| Human acceptance | Consolidated guide and secure temporary-credential retrieval prepared | Not yet requested; complete blocked technical checks first |
| Curriculum | All new content remains unpublished; historical snapshots preserved | Five genuine independent reviews and publication authorization |
| Public deployment | Not performed | Separate explicit owner approval, legal/retention/operations review |

The mail test's initial assertions incorrectly assumed generic201 duplicate
registration and400 malformed-token responses. They were corrected to the actual
existing409 and schema422 contracts while retaining separate400 unknown-token and
expired/consumed-link checks. The initial workload probe stopped at a harness-only
worker-token lookup error; the corrected complete rerun is the measured result.
The first accessibility run failed; no rules were disabled in the passing rerun.

## Controlled workload measurements

Five clients,20 reads per route, no public traffic. p95 milliseconds:

| Operation | p95 |
| --- | ---: |
| Concurrent login (five samples) | 308.19 |
| Course library | 74.15 |
| Grammar | 103.98 |
| Assessment catalog | 548.15 |
| Progress | 35.67 |
| 300-message conversation,100-message bounded page | 219.21 |
| Redis PING (50 samples) | 36.39 |

The read window was3.63s. API working set increased from135,753,728 to141,402,112
bytes; peak working set was471,166,976 bytes. CPU consumption averaged109.76% of
one core across its threads, not109.76% of the entire machine. Seven PostgreSQL
connections were observed; Redis used1,274,960 bytes. The two actual AI requests
took13.70s and19.06s. Piper took6.51s and transcription5.39s. These are a small
local workload and one warm/cold mix, not a sustained capacity claim. The installed
WSL environment reported about7.8GB RAM before image/runtime work. GPU capacity
was not established. No read-path latency target failed, so no speculative
performance rewrite was made.

## Safe continuation

1. Obtain explicit backup-first authorization for Ubuntu recovery to D:. Do not
   repeat the rejected remount or bypass it. Record an actual backup before any
   repair or relocation. Do not reset/unregister a distribution or delete volumes.
2. Confirm C: headroom and Ubuntu filesystem health; verify existing contents and
   stop only owned test services. Reconfigure disposable container storage on D:.
3. Complete local HTTPS, secure cookie/CORS/CSRF, restart/persistence and network
   isolation checks; finish or explicitly bound container inference/scanning.
4. Run final regression groups against fresh disposable namespaces so intentional
   rate-limit tests do not contaminate later login tests. Keep all gated/skipped
   browser coverage distinct from executed coverage.
5. Repeat backup/fingerprints, actual security scans and the release checklist.
   Only then request the single human microphone/screen-reader acceptance session.

New reproducible assets: `backend/scripts/rc_test_controls.py`, `rc_load.py`,
`app/services/erasure_reconciliation.py`, corresponding PostgreSQL tests,
`frontend/e2e/mail-security-live.spec.ts`, `accessibility-live.spec.ts`,
`deploy/compose.rc.yml` and `deploy/Caddyfile.rc`. The `m10_local.py --mailpit`
mode forces local SMTP; `verify --suite curriculum|coach` reuses existing guarded
browser runners. Private daemon tooling and credentials remain ignored.
