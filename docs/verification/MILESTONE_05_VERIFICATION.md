# Milestone 05 verification

Date: 2 November 2026 (Europe/Paris). Status: **implemented and locally verified**, with the product limitations below. No Milestone 06 features were implemented. No accounts, curriculum, attempts, sessions or progress were deleted from either application environment. Test-created accounts and records live only in dedicated test databases.

## Architecture and delivered behavior

FastAPI owns authentication, source permission checks, SQL retrieval, centrally selected CEFR/mode policies, bounded memory, text generation and validation. An injectable Ollama adapter has model-health checks, HTTP and connection limits, one concurrent generation per configured process by default, and no model downloads, fallback, autonomous tools or unbounded retries. Next.js reuses existing authentication and CSRF-aware API helpers.

Five modes: explanation (`tutor`), vocabulary, grammar, structured sentence correction and roleplay. Twenty original, clearly attributed practice prompts span exactly A1, A2, B1, B2, C1 and C2. These prompts are separate from reviewed course content. Conversation level is captured from saved preferences; changing preferences never rewrites historical levels. Start a new conversation after explicitly choosing another level.

Authorized lexical SQL retrieval searches published course/lesson context and linked vocabulary, word senses, grammar explanations/examples, conjugations, dialogues and objectives. Developer preview uses exactly development + enabled flag + admin. Source containers are real lesson foreign keys and versions, ranked deterministically and bounded to three compact contexts. Exercise keys and saved grading snapshots never enter retrieval. Context supplied to the model is labeled `curriculum_context` or `draft_preview`, not blanket curriculum verification. With no sources, answers are labeled `general_knowledge`. The UI supplies trusted source links; provider-generated citations/URLs are rejected.

PostgreSQL persists full conversations and turns. Model context uses at most 12 successful recent messages and 8,000 history characters. Full history has 100-turn-row cursor pages and a 1,000-message conversation cap. Stable request UUIDs, unique constraints and expiring fenced generation leases support safe replay, concurrent-message rejection and interrupted-work recovery without holding a transaction during inference. Sources and preview permission are rechecked on reads, feedback, replay and after generation; revoked/withdrawn/version-changed source history becomes unavailable without deleting its rows.

Recommendations are deterministic lesson-topic reviews, triggered by at least two actual incorrect attempts in a lesson among the latest 200 incorrect attempts at the selected level. Persisted reasons include real activity IDs and accessible lessons. Insufficient evidence produces a neutral introductory suggestion. No invented topic weakness or formal proficiency assessment is shown.

## Changed files

Created:

- `backend/app/ai/__init__.py`
- `backend/app/ai/models.py`
- `backend/app/ai/response_schemas.py`
- `backend/app/ai/orchestrator.py`
- `backend/app/ai/prompts.py`
- `backend/app/ai/retrieval.py`
- `backend/app/ai/scenarios.py`
- `backend/app/ai/recommendations.py`
- `backend/app/ai/providers/__init__.py`
- `backend/app/ai/providers/base.py`
- `backend/app/ai/providers/ollama_provider.py`
- `backend/app/api/v1/ai.py`
- `backend/alembic/versions/20261102_0005_ai_french_tutor.py`
- `backend/tests/test_ai.py`
- `backend/tests/test_ai_postgres.py`
- `backend/scripts/ai_e2e_server.py`
- `backend/scripts/ollama_smoke.py`
- `backend/scripts/verify_ai_migration.py`
- `backend/scripts/verify_ai_restart.py`
- `frontend/lib/ai.ts`
- `frontend/components/tutor-shell.tsx`
- `frontend/components/ai-learning.tsx`
- `frontend/app/ai-tutor/page.tsx`
- `frontend/app/ai-tutor/[conversationId]/page.tsx`
- `frontend/app/ai-tutor/history/page.tsx`
- `frontend/app/ai-tutor/scenarios/page.tsx`
- `frontend/app/ai-tutor/recommendations/page.tsx`
- `frontend/e2e/ai-tutor.spec.ts`
- `frontend/e2e/ai-api.spec.ts`
- `docs/architecture/ai-french-tutor.md`
- `docs/ai/ollama-setup.md`
- `docs/ai/tutor-prompt-design.md`
- `docs/security/ai-tutor-security.md`
- This verification report.

Modified: `backend/app/config.py`, `backend/app/main.py`, `backend/alembic/env.py`, `frontend/app/dashboard/page.tsx`, `frontend/playwright.config.ts`, `frontend/e2e/auth-flow.spec.ts`, `frontend/e2e/learning-flow.spec.ts`, `.env.example`, local `.env` (AI settings only), both Compose files, and README. Existing browser mocks now respect configured isolated ports/origins. Generated build/test caches are not implementation deliverables. No project dependency versions were changed. Python and TypeScript formatters were run without adding runtime dependencies.

This workspace root has no `.git`; only the nested frontend has a Git repository, with pre-existing Milestone 01–04 changes. No commits, reset or cleanup of pre-existing changes were performed.

## Database and migration

Observed deployed head before edits: `20261102_0004` on both application databases. New additive migration: **`20261102_0005`**, now applied to both. New tables:

| Table | Purpose |
|---|---|
| `ai_conversations` | Owner, fixed level/mode/scenario, preview state, provider and fenced generation lease |
| `ai_messages` | User/assistant text, request UUID, status, grounding, safe supplied metadata |
| `ai_message_sources` | Real lesson source FK, content version, deterministic retrieval score |
| `ai_practice_feedback` | Validated correction feedback tied to owner, message and conversation |
| `ai_learning_recommendations` | Explainable, persisted current-level practice suggestions with activity evidence |

Fresh isolated `fluentloop_m05_fresh`: complete migration chain, downgrade only 0005 → 0004, re-upgrade passed. Populated isolated `fluentloop_m05_verify`: additive upgrade, safe test-only downgrade and re-upgrade passed. All pre-M05 row counts and content hashes stayed unchanged across the populated migration sequence: 3 users/profiles/preferences, 10 lessons, 6 courses, 20 units, 3 learning sessions, 15 session exercises, 6 attempts, 3 progress rows and 9 activity events at the time of that check. Later isolated tests added further test records without touching application databases.

Downgrading removes AI memory tables. That destructive rollback was run only on the explicitly named disposable databases, never main or preview. No `down -v`, volume reset, database recreation, publication command or ordinary-user privilege elevation was used.

## Provider and live-model observations

- Host Ollama API version: **0.40.13**.
- Actual tested model: **`llama3.2:3b`**, exact installed tag confirmed by `/api/tags`; Q4_K_M, 3.2B parameters, 2,019,393,189 bytes on disk.
- Resources observed: approximately 16 GB system RAM; approximately 2.7 GB free at the initial check; RTX 3050 laptop GPU, 4 GB VRAM, approximately 2.4 GB initially free. Storage check later showed approximately 20 GB free on C: and 281 GB on D: (decimal units; values fluctuate).
- Windows-host service listener verified as **127.0.0.1:11434**. Both Docker backends successfully reached `http://host.docker.internal:11434` and reported configured-model health `True`.
- Configured limits: 60-second request timeout, 600 output tokens, 4,000 input characters and one generation slot per backend process.
- No model download or silent model substitution occurred. No throughput or broad linguistic benchmark is claimed.

Genuine model checks passed for A1 explanation, grammar, draft-context source associations, structured correction, roleplay opening/follow-up and saved conversation reconnect. A separate direct-provider script passed both correcting “Je suis 24 ans.” to “J’ai 24 ans.” and preserving valid “Je suis étudiant.” It also exercised a no-curriculum A1 question, a refused local endpoint, an absent configured model, and a real one-second inference timeout. The shared Ollama service was never stopped to simulate outage.

An initial live correction incorrectly accepted the age error. Explicit correction guidance was added and the live test now asserts the actual expected correction. The revised samples passed; this is not certification of arbitrary generated French. Existing published content remains unavailable because the ten A1 lessons are unapproved drafts. Live retrieval testing therefore used authorized preview in the isolated database; published-source retrieval and withdrawal were tested deterministically on isolated fixture content.

The optional containerized Ollama profile is internal-only, has no public port and performs no startup download. Compose configuration was validated; that alternative profile was not launched because the verified host service was used.

## API and frontend

All paths below are under `/api/v1/ai`; all are authenticated, and mutations preserve Origin/CSRF and rate limits:

| Method | Path |
|---|---|
| GET | `/health` |
| GET, POST | `/conversations` |
| GET, PATCH | `/conversations/{conversation_id}` |
| POST | `/conversations/{conversation_id}/messages` |
| POST | `/conversations/{conversation_id}/archive` |
| GET | `/conversations/{conversation_id}/feedback` |
| GET | `/scenarios` |
| POST | `/scenarios/{scenario_id}/start` |
| POST | `/corrections` |
| GET | `/recommendations` |
| POST | `/recommendations/refresh` |

Frontend routes: `/ai-tutor`, `/ai-tutor/[conversationId]`, `/ai-tutor/history`, `/ai-tutor/scenarios`, `/ai-tutor/recommendations`. Dashboard AI Learning cards show independent availability, recent conversation, review suggestions and scenario navigation. The accessible chat supports Enter submission, pending/error states, stable retry IDs, title editing, source links, preview labels, correction originals/alternatives and older-message loading. Stored content is rendered as React text.

## Executed checks

| Category | Actual result |
|---|---|
| Existing backend baseline | All 36 pre-existing tests passed before tutor implementation |
| Final deterministic backend regression | 71 passed; 1 opt-in PostgreSQL test skipped in the default run; two existing dependency deprecation warnings |
| Opt-in real PostgreSQL test | 1 passed separately: actual concurrent requests, replay uniqueness, reconnect persistence, real server-graded mistake evidence and recommendation persistence |
| Optional live Ollama + PostgreSQL run | 1 passed separately: genuine tutor, grammar, correction and roleplay responses with database persistence and reconnect |
| Direct live provider smoke | Passed: erroneous/valid French correction samples, general A1 answer, missing model, refused connection and real timeout |
| Actual API process restart | Passed: existing saved conversation read, continued and replayed idempotently after test API restart |
| Fresh and populated migration checks | Passed; populated old-data row counts and hashes preserved across upgrade / downgrade / re-upgrade |
| Frontend typecheck | Passed |
| ESLint | Passed |
| Production Next.js build | Passed; all five tutor routes compiled/prerendered under the existing Next.js 16 cache-component behavior |
| Full browser suite | 10 passed, 1 optional M04 smoke skipped in that run |
| Optional existing M04 browser smoke | 1 passed separately on the isolated database: real lesson grading, 80% result, persistence, progress, replay and learner denial |
| Main and preview Compose configuration/build | Passed |
| Main and preview runtime | All five services in each stack healthy; both heads 0005 and configured model health True |

The six tutor UI tests mock the API boundary. The additional tutor browser test uses real authentication, FastAPI and PostgreSQL with a deterministic fake inference provider. Existing full registration/onboarding/settings browser checks also ran against the isolated API/database and local Mailpit. The live-model category above uses genuine Ollama, not those mocks. Default test skips are explicit opt-ins, not reported as live-model passes.

Backend coverage includes all six policies; mode/length/extra-field validation; provider configuration, timeouts, metadata and output bounds; JSON corrections; stable ranking and empty retrieval; draft matrix; source links and withdrawal; preview revocation including during generation; owner isolation; CSRF; history truncation; neutral/evidence-backed recommendations; failed-turn recovery; lease expiry; request replay; rate limits/body caps; and application-boundary injection defense. Tests verify no transaction remains open during the provider call. These boundary checks do not prove an LLM universally resists prompt injection.

## Preservation and Docker health

Aggregate application counts before and after upgrade:

| Environment | Users | Lessons | Draft lessons | Learning sessions | Attempts | Progress |
|---|---:|---:|---:|---:|---:|---:|
| Main, before and after | 2 | 10 | 10 | 0 | 0 | 0 |
| Preview, before and after | 2 | 10 | 10 | 3 | 11 | 2 |

The PostgreSQL, Redis and Mailpit containers/volumes were retained. Only backend/frontend containers were rebuilt/recreated. Preview database/Redis addresses remain separate from main. Both readiness endpoints remained healthy after application updates. Ordinary users were not promoted; admin test accounts were created only in the isolated test database. All A1 draft publication states remain unchanged.

## Limitations and next scope

- Small-model answers can still contain grammar mistakes; the measured correction failure and fix are disclosed above. Broader independent French evaluation, especially at C1/C2, remains necessary.
- Retrieval is bounded lexical search, with limited candidate expansion and lesson-level source containers; no sentence-level factual entailment or semantic search is claimed.
- Recommendations currently identify lesson-topic review needs, not fine-grained grammatical diagnoses. They are available separately rather than injected into every model prompt.
- Scenario prompts are original practice situations, not expert-reviewed course material. Roleplay summaries are free-form; only sentence-correction feedback is structurally persisted in the feedback table.
- Generation is synchronous and non-streaming. A browser disconnect may leave its worker running; leases and replay allow recovery. Concurrency limits apply per process, not across both stacks sharing the same host model.
- No automatic conversation deletion/export/retention job is introduced. Define an operational retention policy before public deployment. Archive retains data.
- Host Docker Desktop routing was tested; alternative Linux routing and the optional container Ollama profile were not runtime-tested.
- No voice, STT, TTS, acoustic scoring, subscriptions or payments were added.

Exact Windows PowerShell setup, isolated test and verification commands are in [Ollama setup](../ai/ollama-setup.md). Suggested future Milestone 06 scope: independent French quality evaluation, measured retrieval improvements, finer topic tagging from real exercise associations, operational retention/export controls and robust distributed model scheduling as deployment needs justify. Voice work requires its own separately approved milestone. Nothing from that scope was implemented here.
