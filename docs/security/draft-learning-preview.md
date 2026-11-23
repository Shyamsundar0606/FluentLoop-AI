# Draft Learning Preview Security Policy

## Default and production behavior

Draft learning preview is disabled by default. Access requires all of the following:

1. `APP_ENV=development`.
2. `ENABLE_DRAFT_LEARNING_PREVIEW=true`.
3. The authenticated user has the existing `admin` role.

The settings property `draft_learning_preview_enabled` evaluates to false outside development, even when the preview flag is true. Do not configure production with development environment values. Preview access does not publish or modify curriculum records.

Ordinary users continue to receive published content only. An additional personal
learning-only grant is available in development: `ENABLE_PERSONAL_LEARNING_PREVIEW=true`
and `PERSONAL_PREVIEW_USER_IDS=["confirmed-learner-uuid"]`. Both frontend origin and
all CORS origins must be loopback origins. The user must be an active, verified
learner. The grant defaults off and cannot be enabled by a browser request.
Bind the API to loopback as the personal launcher does; origin configuration is
an additional gate, not a substitute for listener/network isolation.

Personal preview reuses the existing `preview_mode` session marker, ownership,
grading and per-request authorization. Revocation hides retained preview sessions
and answers without deleting them; restoring the grant restores access. Existing
preview exclusions from published-only analytics and XP remain in effect. No
schema, lesson version, publication status or frozen answer key is changed.

Learning preview and curriculum authoring now use separate predicates. The personal
grant does not permit review-console access, draft edits, independent reviews or
publication. Administrator authoring retains the original development/admin gate.
Never replace a content-authoring permission check with the learning-preview check.

## Data and grading controls

Preview authorization is checked on each request, not only when the session is created. If access is revoked, the user's underlying session, answers, and progress remain stored; they are not deleted or exposed by session lists, progress totals, dashboard aggregates, or recent activity. Re-enabling a valid development preview authorization permits the same admin to access the retained data again.

Answer keys are stored in the database only in server-side snapshots. Unanswered session responses omit answer keys, correct answers, explanations that could disclose the key, and correctness flags. Feedback is available only after the authenticated learner answers. Mutating routes require the established Origin and CSRF checks. Session ownership is verified for each session operation.

## Operator guidance

- Keep `ENABLE_DRAFT_LEARNING_PREVIEW=false` unless a specific development preview is required.
- Never grant an existing user's admin role solely to enable preview without approval.
- Do not use preview for content publication or independent linguistic/licensing review.
- Do not clear Redis or database records to disable preview; changing the flag or admin role is sufficient.
- Review [the learner guide](../learning/learner-guide.md) and [the interactive learning architecture](../architecture/interactive-learning.md) for user-visible behavior and stored learning data.
