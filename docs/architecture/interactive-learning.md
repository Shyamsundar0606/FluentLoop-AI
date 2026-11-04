# Interactive Learning Architecture

## Scope

Milestone 04 adds durable learner sessions and progress to the existing six-level French curriculum. The first supported graded exercise type is multiple choice. Sessions require an authenticated learner; state-changing API calls use the existing Origin and CSRF protections.

## Session lifecycle

`POST /api/v1/learning/sessions` validates that the lesson is visible to the user, snapshots its learner-facing lesson material and supported exercise data, and creates a session. A unique partial index allows at most one `in_progress` session for a user and lesson. Starting the same lesson again returns that active session; after completion or abandonment, a new attempt may be started.

Each session records the source content version and level. Exercise prompts, options, feedback text, and correct-option IDs are frozen in server-side session snapshots, so editing curriculum content does not change an existing session's grading. Unanswered API responses do not include answer keys or correctness. The API returns grading feedback only after the learner submits an answer.

Answers are checked by the backend. A session lock serializes submissions, unique constraints prevent multiple answers for one frozen exercise and duplicate idempotency keys, and an identical retry returns the saved result. A conflicting retry or answer to a completed session is rejected. Completion is allowed only after every required exercise has an attempt.

Sessions move from `in_progress` to `completed` or `abandoned`. Completed sessions are immutable. Abandoning preserves saved attempts but does not award completion. Starting any session creates/updates per-user lesson progress; completion updates latest/best score and completion count. Progress is keyed by user and lesson rather than the current account level, so a learner can change levels and revisit earlier work.

## Persistence

The additive `20261102_0004` migration creates:

- `learning_sessions`: owner, lesson/version/level, frozen lesson snapshot, lifecycle, progress positions, and score totals.
- `learning_session_exercises`: ordered frozen exercise snapshots and answer keys.
- `exercise_attempts`: one graded answer per frozen exercise with idempotency key and saved feedback.
- `lesson_progress`: per-user/per-lesson status, timestamps, latest and best scores, and completion count.
- `learning_activity_events`: per-user session and progress activity.

Foreign keys preserve referential integrity and cascade learner-owned learning rows when an account is deleted according to the existing account deletion behavior. Existing users, preferences, curriculum, and content publication state are unchanged by this migration.

## APIs and frontend

The learner UI starts or resumes a course lesson, displays saved lesson content, submits exercises, shows server feedback, supports leaving and resuming, presents completion results, and lists progress. The dashboard reads aggregate stats and active sessions from `/api/v1/learning/dashboard`. The selected CEFR level filters the dashboard learning path; course browsing and prior progress remain available independently of that selection.

The API provides:

- `POST /learning/sessions` and `GET /learning/sessions`
- `GET /learning/sessions/{id}` and `POST /learning/sessions/{id}/resume`
- `POST /learning/sessions/{id}/answers`, `/complete`, and `/abandon`
- `GET /learning/sessions/{id}/results`
- `GET /learning/progress`, `/learning/progress/lessons/{id}`, and `/learning/dashboard`

Every query scopes user-owned session and progress data to the authenticated user. List totals and dashboard aggregates also filter content by current visibility, preventing hidden draft records from leaking after preview access is revoked.

## Limits

This milestone does not add AI tutoring, speech or pronunciation scoring, billing, subscriptions, non-multiple-choice grading, or curriculum publication. A lesson without gradable multiple-choice exercises cannot start as a learning session.
