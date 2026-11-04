# Adaptive learning engine (Milestone 07)

The Home dashboard obtains a persisted daily plan from FastAPI. Plan selection, vocabulary grading and review scheduling run locally without Ollama. Existing lesson, AI and speech systems supply the actual learning activities; there is no second tutor or speech engine, paid service, cron job or new worker.

## Modules and storage

- `app/services/daily_learning_service.py`: learner context, ranking, persisted plan generation, activity linking and trusted completion.
- `app/services/study_content.py`: current lesson/vocabulary publication and RBAC filters, authorized answer alternatives and content digests.
- `app/services/spaced_repetition_service.py`: card enrollment, sessions, immutable answer snapshots, transactional grading, schedule/history persistence.
- `review_grading_service.py`, `review_scheduler.py`, `study_clock.py`: deterministic answer normalization, versioned interval computation and UTC/IANA study-date handling.
- `app/study_models.py`, `study_schemas.py`, `api/v1/study.py`: six additive tables, typed private API contracts and authenticated routes.

Migration `20261104_0008` follows inspected head `20261102_0007`. Tables are `daily_learning_plans`, `daily_learning_activities`, `spaced_repetition_cards`, `vocabulary_review_sessions`, `vocabulary_review_session_items`, and `spaced_repetition_reviews`. Review session items are necessary for an ordered, private answer snapshot; they are not fabricated historical attempts. No existing tables or rows are backfilled or replaced. Milestone 05 recommendation tables remain intact; the planner derives current evidence directly rather than duplicating those tables.

## Learner context

Use the authenticated user, saved CEFR level, explanation language, learning goal, study duration, focus and IANA timezone. Read current authorized curriculum, saved unfinished sessions, completed lessons, recent exercise attempts and permitted due cards. The planner does not use email, password hashes or age, and makes no model requests.

Exactly A1, A2, B1, B2, C1 and C2 are supported. Nothing changes the saved level automatically. Plans/cards/reviews retain their level context when the learner switches levels. A1 new vocabulary is enrolled in unit/lesson/vocabulary order, starting with the first permitted material rather than random database UUID order.

## Deterministic ranking (`priority-v1`)

| Candidate | Priority | Evidence |
|---|---:|---|
| Due vocabulary | 100 | Actual permitted cards with `next_due_at <= now` |
| Continue lesson | 90 | Owned, unfinished, currently permitted learning session |
| Revisit lesson | 80 | Unresolved incorrect attempts from the latest 200 attempts at this level |
| New vocabulary / next lesson | 60 | Authorized unseen vocabulary / curriculum order excluding completed or active lessons |
| Tutor / speaking | 10–35 | Saved focus and recognized goal; level-appropriate general practice |

An exercise has a reliable lesson association but no explicit grammar/vocabulary-topic key in the existing schema. Therefore errors produce **lesson-level** recommendations, not invented claims about être, articles or another topic. Keep references to actual incorrect attempt IDs. Only current-source exercise/lesson/version links qualify. A later correct attempt clears the older error streak for that source exercise; the original attempts remain unchanged. Multiple unresolved mistakes break ties by their actual evidence count, then stable lesson identity. With no mistakes, return neutral next-material/practice reasons.

Writing/reading focus favors tutor practice; speaking/listening focus favors speaking. Daily-conversation/living-in-France goals favor speaking; work/university/exam goals favor tutor practice. Unknown/free-text goals do not become model prompts or arbitrary titles. Ranking reasons are short and visible; numeric priorities are implementation rules, not AI confidence scores.

## Selection and completion

Allocate up to two minutes for a three-card review, up to five for one lesson candidate, and up to ten per distinct tutor/speaking activity. Use the remaining budget among available real tasks. Do not clone filler tasks or pretend a 30-minute goal was fulfilled when only 20 or 27 realistic minutes are planned. All durations are estimates, never measured study time.

Create linked owned records atomically on explicit Start. A lesson uses the existing session service with an optional shared-transaction mode; default behavior of existing lesson endpoints is unchanged. AI/speech activities create the existing conversation/session records without inference. The actual conversation and speech requests still use their existing security, quota, validation, memory and privacy paths.

Daily activity completion comes from the linked review session finishing with an actual answer, the linked lesson completing, a successful tutor reply, or a successful transcribed/user-confirmed speech turn. Opening a page, failed generation, silence and unusable/non-French speech do not count. Fetching a saved plan reconciles these trusted states; explicit completion also checks the same rules.

## Publication permissions

Use `can_preview_drafts`, with development environment, enabled backend flag and admin role all required for draft access. Course, unit and lesson statuses must all be permitted. Normal learners only receive published content. Recheck access on plan retrieval/start/completion, card selection, review retrieval and answer submission. Revoked or version-changed content is hidden, while historical result metadata stays stored. The existing ten A1 drafts remain unpublished and have no fabricated review approval.

Without published content, ordinary learners receive tutor/speaking alternatives, no fake course links and no draft cards. If inference is offline, generation/persistence and any permitted non-model reviews/lessons continue to work; model-dependent practice reports its existing outage. No offline curriculum is invented to fill the gap.

See [daily plans](../learning/daily-study-plan.md), [scheduler](../learning/spaced-repetition.md), [security](../security/adaptive-learning-security.md) and [actual verification](../verification/MILESTONE_07_VERIFICATION.md).
