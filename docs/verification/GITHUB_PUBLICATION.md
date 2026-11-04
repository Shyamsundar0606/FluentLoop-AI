# GitHub publication verification

Date: 2026-11-04. Scope: credential remediation and publication of existing Milestones 01â€“07; no Milestone 08 or learning-feature implementation.

## Credential remediation

Sanitized `.env.example`, both Docker Compose files, `backend/app/config.py`, `backend/alembic.ini`, `.github/workflows/ci.yml`, `README.md`, `docs/ai/ollama-setup.md`, `docs/speech/faster-whisper-setup.md` and `docs/verification/MILESTONE_07_VERIFICATION.md`.

Both main and preview PostgreSQL roles received independent cryptographically random passwords. New authentication succeeded and fresh connections using old credentials failed. Private `.env` was updated atomically with restricted local permissions. No password values appear in this report. Compose now requires private environment values, application/Alembic defaults contain no credentials, and the example template contains only nonfunctional placeholders. CI creates fresh isolated credentials on each disposable runner.

Only main and preview backends were rebuilt/recreated to reconnect. Database, Redis, email, frontend and speech-worker services were retained. Both readiness endpoints confirmed database and Redis connectivity; all twelve main/preview services were healthy.

## Data preservation

The rotation itself preserved count-and-content fingerprints for all 59 public tables in each database. No database or volume was recreated or deleted, and no new application migration was added.

After backend reconnection, all 59 main tables and 58 preview tables still matched byte-for-byte row fingerprints. Preview's existing startup content importer refreshed `lexemes` timestamps. Its row count was preserved; a repeat import inside a rolled-back transaction reproduced timestamp-only churn while the semantic hash excluding `updated_at` remained unchanged. All account, auth-session, progress, AI, speech and review-history table fingerprints remained unchanged. The original pre-restart snapshot retains aggregate hashes, not a row-level backup, so this report distinguishes that timestamp exception from exact full-table equality.

## Repository and security audit

The original clean frontend starter commit `6f686f6` is retained as the top-level publication commit's ancestor, without rewriting it. Nested `frontend/.git` metadata was moved to a protected ignored backup only after verifying the root repository had its original commit. No nested Git metadata or gitlinks are distributed. The remote was inspected and had no refs before publication; no force push is used.

The root ignore rules exclude private environments, backups, database files/volumes, recordings/generated audio, model weights/caches, logs, Python/Node caches and raw local verification artifacts. Attributed public Ogg test fixtures and one visually reviewed synthetic-account screenshot are intentionally included. The full source, eight existing migrations, draft curriculum, tests, Docker configuration and safe documentation are included.

Exact active and retired credential scans found no matches in publication candidates. Private-key, provider-token, GitHub-token, AWS-key, JWT and literal PostgreSQL-password checks passed. No non-example learner email addresses were found in source/documentation candidates. Preserved starter history passed both the exact-value scan and Gitleaks 8.30.1. Gitleaks flagged three deterministic test-password lines; review confirmed synthetic isolated-fixture values, and `.gitleaks.toml` allows only those exact strings in the two test files. It does not allow deployment credentials or whole test directories.

## Executed verification

- Backend: **203 passed**, zero skips, including native audio decoding and isolated PostgreSQL migration/persistence/concurrency checks. Two existing dependency deprecation warnings.
- Frontend: ESLint, TypeScript and production build passed; 35 pages generated. Static checks reran after the focused test-locator correction.
- Browser: account/text/lesson mock suite **11 passed**; responsive/voice suite **9 unique scenarios passed** across isolated runs; M07 real-PostgreSQL browser suite **3 passed**. Live M04 server-graded lesson/persistence/authorization scenario **1 passed**: **24 unique Playwright scenarios passed in total**, across isolated runs.
- Actual local speech inference: Base CPU int8 recognized the public human French fixture and a synthetic French phrase; Piper produced 112172 bytes of WAV audio; silence returned `no_speech`. No private recording was used. This is not acoustic pronunciation validation.
- Both Compose configurations validated and both backend images built. Both application readiness endpoints passed after reconnection. Secure environment generation produced independent random values, replaced every placeholder and refused to overwrite an existing file.

Initial browser attempts used mismatched origins or reached the existing per-user speech quota. Those runs failed; isolated reruns with matching origins and fresh test state passed without weakening application limits. One pre-existing broad status locator was narrowed after M07 introduced a second status message; only the test changed.

Ten A1 lessons remain unpublished pending independent review. Acoustic pronunciation scoring remains unvalidated and unavailable. Raw test reports, fixture-account details, recordings and local remediation/recovery files remain private and excluded.

Final index review: 254 files, no private paths, nested Git metadata or gitlinks. Exact-value/index checks and the independently exported staged-tree Gitleaks scan passed. The pathless patch scan reported only the same three reviewed synthetic fixture literals. Two pre-existing whitespace issues were removed; their non-whitespace source content was verified unchanged. No application feature changes or new migrations were introduced.

CI hardening: generated ephemeral credentials are registered with GitHub Actions log masking before environment export. CI mode refuses execution outside an Actions environment. Local tests confirmed mask registration and the non-CI guard without displaying generated values.
