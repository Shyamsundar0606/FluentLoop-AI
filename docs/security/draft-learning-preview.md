# Draft Learning Preview Security Policy

## Default and production behavior

Draft learning preview is disabled by default. Access requires all of the following:

1. `APP_ENV=development`.
2. `ENABLE_DRAFT_LEARNING_PREVIEW=true`.
3. The authenticated user has the existing `admin` role.

The settings property `draft_learning_preview_enabled` evaluates to false outside development, even when the preview flag is true. Do not configure production with development environment values. Preview access does not publish or modify curriculum records.

Ordinary users continue to receive published content only. Draft and review content is returned as not found for direct learner requests, including course, lesson, session, and progress operations. A preview session stores a `preview_mode` marker and remains inaccessible when the preview setting or admin role is removed.

## Data and grading controls

Preview authorization is checked on each request, not only when the session is created. If access is revoked, the user's underlying session, answers, and progress remain stored; they are not deleted or exposed by session lists, progress totals, dashboard aggregates, or recent activity. Re-enabling a valid development preview authorization permits the same admin to access the retained data again.

Answer keys are stored in the database only in server-side snapshots. Unanswered session responses omit answer keys, correct answers, explanations that could disclose the key, and correctness flags. Feedback is available only after the authenticated learner answers. Mutating routes require the established Origin and CSRF checks. Session ownership is verified for each session operation.

## Operator guidance

- Keep `ENABLE_DRAFT_LEARNING_PREVIEW=false` unless a specific development preview is required.
- Never grant an existing user's admin role solely to enable preview without approval.
- Do not use preview for content publication or independent linguistic/licensing review.
- Do not clear Redis or database records to disable preview; changing the flag or admin role is sufficient.
- Review [the learner guide](../learning/learner-guide.md) and [the interactive learning architecture](../architecture/interactive-learning.md) for user-visible behavior and stored learning data.
