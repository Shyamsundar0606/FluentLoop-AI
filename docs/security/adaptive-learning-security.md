# Adaptive learning security

All study/review routes derive identity from the existing authenticated cookie session. No endpoint accepts an arbitrary user ID or a client-controlled preview bypass. Mutations use existing origin validation and double-submit CSRF. Existing auth, verification, password hashing, cookie policy and quotas are unchanged. New study mutations are limited to 60/minute per user and reads to 240/minute; Redis failures fail closed through the existing limiter. Private responses use `Cache-Control: no-store` and `Pragma: no-cache`.

## Content and answer boundaries

Filter by saved CEFR context and current course/unit/lesson status. Drafts require the existing development-only flag and admin RBAC together. Production cannot activate preview through that flag. Recheck authorization on plan retrieval/start/completion, enrollment, due queries, session retrieval and grading. Existing linked conversations revalidate their historical curriculum sources through the original tutor authorization path.

Review alternatives come solely from authorized source records. If any alternative comes from draft content, the card is labeled draft preview. Current permission or content-digest changes hide/reject stale snapshots. Do not expose an old answer by replaying a request after access has been revoked. Metadata-only history retains correctness, scheduling dates and versions without leaking protected source text.

Private answer snapshots never appear in pre-answer session/question APIs. Feedback is returned only after a valid owned answer submission. Deterministic server grading ignores no authoritative client result: fields such as `is_correct` are forbidden. Recall ratings affect scheduling parameters only; wrong + easy remains wrong and schedules relearning.

## Ownership and concurrency

New plan/card/session tables have explicit user identities, uniqueness and foreign keys. Composite review ownership/context foreign keys prevent attaching another user's card/session item or mismatching an attempt's item/session/card. Existing lesson/conversation/speech links are created by the backend, never accepted as caller-selected links; service checks enforce their ownership and current access without altering legacy table architecture.

Serialize plan generation and session creation on the existing user row. Plans are unique by user/local date/level. Cards are unique by user/sense/level/type. Only one active review session per user/level is allowed. Answer submission locks the owned session and card, then stores the attempt and scheduling update atomically. A unique request UUID and unique item attempt prevent double scheduling. Identical retries return the prior result; conflicting requests fail safely.

Regeneration is explicit and restricted to unstarted plans; cancelled generations remain stored. Completion checks actual linked state rather than accepting page-view claims. User accounts, progress, conversations and review history are never reset or backfilled as imaginary past work.

## Privacy and infrastructure

The planner uses preferences, timezone, learning history and permitted curriculum, with no model calls. Email, password hashes and age are not planner inputs or sent to Ollama. Review records contain only necessary answer/schedule evidence. No extra personal fields, workers, external services, subscriptions or cron jobs were added. Existing speech retention, microphone consent, transcript editing, audio ownership and non-French/silence guards remain unchanged.

Production database migrations are additive only. Rollback experiments run exclusively on generated `fluentloop_m07_*` PostgreSQL databases. Main/preview volumes are not reset. The guarded browser harness requires development + an explicit test flag + an isolated database prefix; it uses real Redis with a fresh test-instance key namespace and unchanged thresholds, never flushing shared keys or weakening application quotas. Browser answer expectations are written to a local test fixture file, not exposed by a learner API.

See [verification evidence](../verification/MILESTONE_07_VERIFICATION.md) for real PostgreSQL concurrency/rollback/isolation, live inference, browser results and data-preservation fingerprints.
