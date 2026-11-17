> Latest checkpoint (2026-11-15): [current implementation and verification](../verification/CURRENT_DEVELOPMENT_CHECKPOINT.md).
> Disposable PostgreSQL/Redis and default Turbopack are now working. The older
> checkpoint descriptions below are historical and are superseded by that record.

# Milestone 10 assessment design

Design prepared on 2026-11-15. The revised owner strategy defers manual acceptance
until the end. All five category interfaces and the remaining skill implementation
are now present. The sections below retain the original architecture decisions.
Current behavior is documented in [assessment and feedback](../learning/ASSESSMENT_AND_FEEDBACK.md).

## Remaining-skill implementation checkpoint

Vocabulary and reading use explicit learning-objective skill metadata and the
existing grading engine. Reading additionally requires linked task context, frozen
into the session. A separate `WritingSubmission` model preserves unscored original
text and advisory feedback. Migration `20261115_0011` has a populated-data rollback
guard. Writing history, retry and revision controls are integrated into Assessments.
All four objective skills and separate writing evidence appear in Progress.

An immutable draft importer reuses existing content helpers and lexical records.
The three original A1 draft lessons contain four vocabulary questions, three reading
questions and a writing prompt. Existing grammar/listening definitions are reused.
No persistent import or migration was performed. Technical completion still needs
the unavailable PostgreSQL/live-browser checks and resolution of the default build.

## Implemented first slice

`assessment_service` groups authorized grammar/listening questions by lesson at the
saved level. Definitions expose lesson version, skill, duration guidance, item count
and `objective-v1` scoring. Sessions select at most 12 questions and use a dedicated
activity key. Existing snapshots, answer projection, grading, idempotency and saved
results remain the normal entry points. No database migration is needed for this slice.

`/learning/assessments` lists definitions, `/sessions` starts or resumes an objective
assessment, `/history` provides bounded pagination and `/insights` summarizes up to
100 most recent assessments at the saved level. History rechecks lesson and topic
permissions through the learning engine. Authorization may leave a sparse history
page. The next offset advances through the underlying session page.

Analytics count objectively graded questions in completed sessions only. They show
insufficient evidence for empty results. The existing M07 planner already reads
these saved incorrect attempts and offers authorized mistake practice, verified by
the new API regression. Session keys prevent assessment completion from updating
ordinary lesson completion or creating vocabulary review schedules.

The first slice integrated Assessments into Learn and shared question/results pages.
The later checkpoint extends this to all five categories and exposes objective
metadata. Real database verification remains pending. Local speech models were
verified separately with a synthetic sample.

## Existing engine boundary

`learning_service.start_session` already selects exercises, freezes the lesson and
exercise content, and separates activity keys from ordinary lesson completion.
`submit_answer` persists graded attempts and idempotency keys. `complete_session`
updates lesson progress only for the `lesson` activity key. Reuse these paths for
objective assessment items, including the existing answer-free exercise projection
and listening authorization. Retain all existing format support and validation.

`interactive_learning.candidates` already filters authorized content by level,
category and optional grammar topic. Reuse the underlying permission predicates.
Question selection must enforce the user's saved level, lesson permissions, topic
permissions and exact approved content versions at selection and subsequent access.
Preview permission remains limited to authorized isolated developer environments.

## Definition and session representation

An assessment definition needs a stable ID, content version, skill, one of A1,
A2, B1, B2, C1 or C2, objectives, duration guidance, publication status and a
validated scoring policy. An exercise format alone cannot establish a skill.
A short-answer item may test reading, vocabulary or grammar depending on its task.
Record explicit reviewed skill metadata and original reading/listening context.

Begin objective assessment sessions with a stable `assessment:` activity key.
Preserve selected question IDs, their versions and the assessment policy in a
private frozen snapshot. The existing engine is lesson-scoped. Initially restrict
one objective assessment session to one authorized lesson rather than silently
discarding questions from other lessons. Expose that scope in the definition.
Cross-lesson selection requires a separately reviewed model change and tests.

Inspect current snapshot validation before adding metadata. Add a definition
table only if versioned source definitions cannot safely provide the required
authoring and publication lifecycle. Do not embed mutable definition lookups in
historical results. Old sessions without assessment metadata retain their behavior.

## Writing practice

Open-ended writing cannot use `ExerciseAttempt.is_correct` or its mandatory points
as a truthful evaluation. Introduce a dedicated writing submission record if the
existing conversation records cannot preserve the task, original text and feedback
without changing their established semantics. A small dedicated table is preferable
to fake correctness or synthetic completed lessons.

Store owner, task ID/version, level, original response, creation time and advisory
feedback independently. Bound response and prompt lengths. Use the existing local
Ollama provider and structured output validation. Distinguish task completion,
possible grammar issues, vocabulary and clarity. On provider failure save the
original submission with feedback unavailable and allow a bounded retry. Never
change saved learning level or produce an objective proficiency score from this
feedback. Treat learner text and model output as untrusted data.

## Results and analytics

Return saved counts and points only for objectively graded items. Zero available
items or zero maximum points produces an insufficient-evidence state. Writing
feedback remains separate. Results include date, objectives, missed topics,
explanations permitted by the frozen policy and paginated previous attempts.

Aggregate owned learning sessions, exercise attempts, review attempts and activity
events. Restrict published content visibility using the existing permission rules.
Exclude draft previews from ordinary learner analytics and recommendations. Keep
lesson completions, focused practice and assessments as separate counts. Derive
grammar accuracy from explicitly tagged items with dates and denominators. Report
reading/listening evidence only from actual comprehension tasks. Show missing
evidence honestly. A single correct answer does not establish mastery.

Reuse M07 `daily_learning_service.recommendations` and existing mistake lookup.
Recommend authorized practice with the actual mistake count and observation period.
Use bounded queries, pagination and measured query plans before adding indexes.
Keep existing review-card due dates and scheduler behavior.

## Proposed endpoints and frontend placement

| Proposed operation | Required behavior |
| --- | --- |
| List assessment definitions | Saved-level and publication filtering, useful empty state |
| Start objective assessment | CSRF, rate limit, stable idempotency and frozen authorized selection |
| Existing session read/resume/answer/complete | Ownership, confidential keys, immutable grading and separate assessment activity |
| Assessment history/results | Owner-only, paginated, saved evidence and snapshot policy |
| Submit writing and request feedback | Preserve original text, request idempotency, bounded validated advisory response |
| Progress analytics | Owner-only aggregates, explicit evidence denominators and level preference |

Add Assessments to the existing Learn area. Extend Progress with skill evidence,
assessment history and improvement suggestions. Preserve the five primary sidebar
destinations. Reuse lesson controls, focus handling, feedback and responsive cards.
Provide task context accessibly before the question. Keep answer keys server-side
until the result policy permits disclosure. Listening failure must allow recovery
without falsely grading unheard content.

## Verification before implementation acceptance

Test authenticated ownership, cross-user denial, invalid IDs, level filtering,
draft protection, frozen answer-key secrecy, duplicate and concurrent submissions,
score integrity, resume, unavailable content, historical snapshots and provider
failure. Use original draft reading passages with validated keys. Test writing
without fabricated correctness. Check that assessment completion never increments
ordinary lesson completion or advances spaced-repetition schedules accidentally.

Run migrations forward and backward in disposable PostgreSQL. Guard rollback
against discarding writing submissions or new assessment metadata. Test API/database
failure recovery and rate limits. Run complete regression suites before calling M10
complete. Speaking remains practice feedback with explicit acoustic-assessment
limitations. Readiness summaries describe evidence and never certify CEFR attainment.
