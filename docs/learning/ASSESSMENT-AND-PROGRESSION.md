# Formative assessment and progression

Version: `formative-evidence-v1`. This is a local design improvement, not empirical
CEFR calibration or a new placement examination. It changes read-only advice on
the learning path; it does not rewrite progress, grades, account levels or roles.

## Evidence that the application can observe

Only the signed-in user's completed full-lesson sessions for the current lesson
version contribute to objective practice advice. Focused practice and older
snapshots remain preserved but cannot establish current full-lesson evidence.
An 80% most-recent score is an explicitly experimental revision cue. Two adequate
attempts on different UTC dates supply a delayed-retrieval indicator; repeated
same-day retries do not. A later low score recommends revision even when an older
best score was high. Zero-point activities cannot satisfy this check.

This is **not** a mastery claim. Available evidence cannot prove unaided transfer,
pronunciation, communicative success or broad listening competence. Saved writing
is evidence of submission only and still requires qualitative review. Productive
tasks do not become passed merely because an AI generated encouraging feedback.
Recommendations never automatically promote a level or lock access to practice.

## Module and level review plans — 23 November 2026

`/checkpoints` supplies 52 module plans and seven sampled level-end plans. It
filters every component through the signed-in account's existing curriculum
permissions. Objective checks reuse the existing per-lesson, frozen, idempotent
assessment engine; histories remain owned by that learner. Completing a component
does not complete its full lesson or change the saved account level.

These are practice plans, not unseen examinations. Questions are drawn from
material already practised. Writing and speaking use stage-specific qualitative
criteria and remain unassessed until reviewed; no numeric aggregate or automatic
CEFR award is generated. A0 remains introductory preparation, not an official
CEFR level. Authentic varied-speaker listening, independently rated productive
work and empirical diagnostic/level-end calibration remain outstanding.

Writing supports up to 8,000 characters for extended advanced tasks. Only that
authenticated writing route receives the bounded 64,000-byte JSON envelope
needed for escaped Unicode. Other AI routes retain their existing request limits,
authentication, CSRF protection, ownership checks and provider context limits.

## Review protocol for each module

1. Diagnostic: try an unfamiliar short task before the model. Record the skill
   needing support; do not assign a CEFR label from a few items.
2. Supported practice: notice the form/meaning, compare examples and check the
   intended answer. Keep scripted listening distinct from spontaneous input.
3. Transfer: use an unseen situation or audience with the same communicative goal.
4. Review open work across task fulfilment, comprehension/source fidelity,
   organisation, language control and interaction/repair. At advanced levels add
   register, modal scope, inference and justified alternative interpretations.
5. Delayed review: retrieve without the original model on a later day; revisit
   errors and compare the revised product with the first version.

The five new depth dossiers contain explicit task-specific criteria. The existing
14 scenario lessons remain staged and unchanged. Module/level-end formal scoring
is still pending, particularly for speaking and varied-speaker listening.

## Calibration work requiring external evidence

Qualified reviewers must judge target-level suitability and item ambiguity;
independent raters must compare open-task ratings and resolve disagreements.
Pilot responses from learners with independently established profiles are needed
to examine item difficulty/discrimination, distractor behaviour, reliability and
fairness. Cut scores require a documented standard-setting process. No such study
has been completed here; synthetic answers and AI review cannot substitute for it.

The [Council of Europe assessment guidance](https://www.coe.int/en/web/common-european-framework-reference-languages/tests-and-examinations)
informs the use of transparent skill profiles. The project's grammar sequence and
task rubrics are design interpretations, not official CEFR syllabus prescriptions.
