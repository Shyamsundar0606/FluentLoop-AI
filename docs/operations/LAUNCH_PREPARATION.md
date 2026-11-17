# Public launch preparation

## RC follow-up and recovery gate

The production API, frontend and speech images built successfully in a separate
Docker29.9.3 daemon with a new private socket/data root. Private PostgreSQL and
Redis passed health checks; container migrations reached0016. The original Docker
Desktop daemon and volumes were not started. Local-only HTTPS and RC Compose
files are prepared, but runtime/certificate/restart checks are not yet verified.

The optional Ollama pull exhausted C: as WSL storage grew and Ubuntu entered
emergency read-only mode. The task-owned daemon was sent SIGTERM and downloads
were stopped. Automatic approval review rejected remounting root read-write due
to filesystem-corruption risk. Do not bypass that decision or reset/unregister
WSL. Backup-first recovery to D: requires owner authorization. Preserve all test
volumes and existing Ubuntu contents. Future image storage requires D: placement
and a free-space preflight with a substantial image/unpacking budget.
See the [RC checklist](../verification/RELEASE_CANDIDATE_CHECKLIST.md).

Preparation only, 2026-11-15. Nothing here authorizes deployment, hosting purchases,
DNS changes, protected migrations or curriculum publication.

## Current deployment boundary

New preparation files are `backend/Dockerfile.production`,
`frontend/Dockerfile.production`, `deploy/compose.production.yml` and
`deploy/Caddyfile`. They are separate from the existing development configuration.
The API uses a non-root process without reload or implicit migrations. The frontend
uses an opt-in standalone build (`FLUENTLOOP_STANDALONE=1`) and a non-root runtime.
Only Caddy exposes host ports; PostgreSQL, authenticated Redis, Ollama and the
speech worker are required private endpoints supplied through operator settings.
No production credentials or infrastructure have been created.

Compose `config --quiet` passed using inert validation-only values. The standalone
build passed and served `/login` and its 46,270-byte CSS asset with HTTP200 on a
temporary loopback smoke server. This verifies the Windows artifact only. Docker
images, Linux runtime, Caddy HTTPS/certificates, persistent-volume permissions and
external private service connectivity remain unverified because Docker's engine
is stopped. Resolve images to reviewed digests and test in isolated staging before
any launch approval. Do not label the configuration production-verified yet.

The existing Compose file is a development setup. The frontend Dockerfile starts
`next dev`; the backend Dockerfile starts Uvicorn with reload. Compose automatically
runs `alembic upgrade head` at backend startup. Do not point this setup at a
protected database to test production readiness. No production image build or
Docker restore rehearsal was executed in this session; Docker's engine was stopped.

## Production design to implement and validate

1. Build immutable frontend assets with the checked lockfile and `npm ci`; run
   `next start` or a validated standalone output as a non-root user. Provide the
   public API origin at build time because `NEXT_PUBLIC_*` values are compiled.
2. Build the API without reload. Run a non-root process with bounded workers and
   request timeouts. Make migrations a separately approved one-shot operation,
   never an implicit web-service boot action on protected environments.
3. Terminate HTTPS at a reverse proxy. Route the frontend and `/api/v1` under the
   chosen public origin, preserve required forwarding headers and bound body sizes
   and timeouts. Validate trusted proxy settings. Keep PostgreSQL, Redis, Ollama
   and speech workers off public interfaces. Do not route worker ports publicly.
4. Set `APP_ENV=production`, secure cookies, explicit CORS/frontend HTTPS origin,
   draft preview disabled, real SMTP credentials and independently generated worker
   service tokens. Store secrets in the host's secret facility; never bake them
   into images, browser environment values, Compose examples or logs.
5. Use separate databases, roles, Redis namespaces, audio paths, secrets and backup
   destinations for development, disposable tests, staging and production. Verify
   database identity and role before every migration or import.
6. Keep inference and speech on private networks with fixed provisioned model
   files. Validate license/attribution for each model/voice. Existing speech limits
   are 2 CPU/2 GB in Compose; these are configuration values, not measured capacity.
   API concurrency and model memory must be measured before selecting a host.

## Backup and migration procedure

Before an approved protected migration, record database name/host/port/current
revision, application release, table counts and history baselines. Create an
encrypted, access-controlled PostgreSQL custom-format backup with a compatible
`pg_dump`. Keep credentials in a private password file or secret environment.
Restore into a new disposable database using `pg_restore --exit-on-error`; compare
history counts and ordered content fingerprints before considering the backup
recoverable. Keep audio retention and backup retention explicitly separate.

This session rehearsed a custom-format backup and restore of the disposable M10
demo only: four learning sessions, eleven frozen exercises, eleven attempts and
one writing submission matched by count and content fingerprint. That does not
prove recovery of a protected database or a full production disaster scenario.

Apply additive migrations first in staging. Current source head is
`20261115_0016`. Migrations 0011–0016 protect writing, revision, motivation,
prerequisite and erasure-recovery/reconciliation data against lossy rollback.
An application rollback must remain
schema compatible; otherwise restore the verified backup into a separate recovery
database and validate it before an approved traffic cutover. Do not bypass a
rollback guard or delete learner records to make downgrade succeed.

Retain the current restricted erasure ledger independently of a backup being
restored. Its account UUID references support replay of later account erasures;
completed receipts expire after 90 days, so backup retention must not exceed that
window. Reapply erasures and verify private-file cleanup before exposing any
restored database. Pending file jobs do not expire until cleanup succeeds. Test
this reconciliation runbook in staging before public use.

## Monitoring and incidents

Monitor API readiness, request errors/latency, database connections/storage,
Redis availability, inference queue/timeouts, speech worker health and expired-audio
cleanup backlog. Readiness must not imply curriculum approval. Redact cookies,
authorization headers, private text, audio and connection strings. Define alert
owners and retention before production, and test alerts with synthetic failures.

For an incident: restrict access or pause the affected service, preserve redacted
diagnostic evidence, identify affected data and release, revoke compromised secrets
or sessions, recover against a verified backup if necessary, validate ownership and
draft protections, then obtain operator approval before restoring public traffic.
Maintain a dated incident record and assess notification obligations with qualified
advice. Do not dump production data into issue trackers.

## Cost worksheet and launch gates

Provider quotes and workload measurements remain pending. Use monthly costs for:
web/API compute + database/storage + private inference CPU/GPU time + speech compute
+ encrypted backup storage + egress + SMTP + monitoring + operational reserve.
No currency estimate is justified by current measurements. Obtain dated provider
quotes only after memory/concurrency requirements and region are chosen; do not
purchase resources as part of this checkpoint.

Launch requires all of the following recorded evidence:

- Dependency advisory remediation and repeated security/regression checks.
- Completed account export/deletion and published retention/processor disclosures.
- Verified production images, HTTPS/proxy behavior, secret rotation and isolation.
- Measured capacity, resource budgets, backup restoration and incident rehearsal.
- One final human microphone, playback, screen-reader and mobile acceptance session.
- Genuine independent curriculum reviews and separately authorized publication.
- Explicit public deployment authorization from the owner.

Track implementation gaps in the
[current checkpoint](../verification/CURRENT_DEVELOPMENT_CHECKPOINT.md).
