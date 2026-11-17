> Latest checkpoint (2026-11-15): [current implementation and verification](../verification/CURRENT_DEVELOPMENT_CHECKPOINT.md).
> Disposable PostgreSQL/Redis and default Turbopack are now working. The older
> checkpoint descriptions below are historical and are superseded by that record.

# Assessment and feedback implementation

## Available categories

Learn → Assessments supports grammar, vocabulary, reading, listening and writing
at the learner's saved level. Availability follows existing lesson and topic
permissions. Ordinary learners see published content. Authorized development
preview accounts can use drafts in the isolated environment.

Objective assessments reuse existing exercise definitions, frozen snapshots,
grading, answer idempotency, session ownership, resume and saved results. Each
session contains at most 12 exercises from one authorized lesson. A dedicated
assessment activity key keeps lesson-completion counts and vocabulary schedules
separate. Definitions expose content version, objectives and duration guidance.

Vocabulary questions require an explicitly vocabulary-tagged learning objective.
The draft release reuses existing lexical records for French-to-English meaning,
English-to-French short answers, matching and contextual choice. Reading requires
an explicitly reading-tagged objective and a linked passage. The passage is frozen
with the session and remains available during questions and saved-result review.
Listening continues to use existing authorized Piper audio and retry controls.

## Original draft release

`backend/content/practice/a1-assessments-0.1.0.json` contains three draft lessons
with seven objective exercises and one unscored writing prompt. It introduces an
original message from Lina and reuses existing greeting vocabulary. All five
independent review categories remain pending. Importing this release creates
separate versioned course and lesson identities. It preserves existing lessons,
keys, progress and snapshots. Repeated imports of identical source reuse the batch.
Changing a previously imported version is rejected. New releases use new versions.

`assessment_content` validates the authoring format for exactly A1, A2, B1, B2,
C1 and C2. Only the A1 draft is supplied. Structural level support does not imply
that six levels of pedagogically reviewed material exist.

## Writing storage and optional feedback

Migration `20261115_0011` introduces `writing_submissions`. It stores the owner,
lesson/version, frozen prompt, original response, request key, creation date,
preview flag, feedback status and separately validated advisory feedback.

Writing text is bounded at 4000 characters and retained exactly as submitted.
Repeated identical request keys return the same record. Reusing a key for different
text returns HTTP 409. A revision creates a new submission. Successful feedback
is reused. Provider failure or invalid output leaves the original submission saved
and permits retry. Database read transactions are released before model inference.
Ownership and content permissions are checked again before saving feedback.

The local Ollama response has bounded fields for task completion, possible grammar
improvements, vocabulary suggestions and clarity. Additional fields are rejected.
The model receives the task, learner response and selected level. Account email,
profile and unrelated conversations are excluded from the prompt. Learner text is
untrusted data. Generated suggestions remain advisory and may be mistaken. Writing
does not receive deterministic correctness, proficiency percentages or certification.

The migration refuses rollback when writing records exist. Persistent application
databases require a separately approved migration and verified recovery plan.

## Evidence and recommendations

Progress summarizes completed objective assessments from at most 100 recent
assessment sessions. It displays question counts and correct-answer counts.
Writing shows saved-submission counts from its own bounded window. Empty evidence
is explicit. Both histories are paginated and recheck permissions on each request.
Permission filtering can produce a sparse history page.

Review recommendations use unresolved questions in the latest 200 exercise
attempts and link to existing mistake practice. The M07 planner already consumes
the same saved attempts. These counts describe recorded practice and never change
the learner's selected CEFR level automatically.

## Current verification limits

See [the regression record](../verification/COMPLETE_REGRESSION_RESULTS.md).
Real local Ollama feedback and an in-memory Piper-to-Faster-Whisper synthetic
pipeline passed. Real PostgreSQL migration/concurrency/recovery and live browser
integration remain pending because PostgreSQL and Redis are unavailable. The
default Turbopack build failure remains separate from the passing webpack build.
Physical microphone and human accessibility checks belong to final acceptance.
