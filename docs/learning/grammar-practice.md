# Grammar and focused practice

Learn has **Lessons | Grammar | Practice** tabs. It uses the learner's saved
CEFR level; lesson and grammar browsers can also browse the existing six levels.
Empty levels explain that authorized content is not available yet.

## Small implementation draft

`backend/content/practice/etre-interactive.json` is an original, AI-assisted
development-only implementation draft, version 0.1.1. It adds one separate draft course/unit/lesson
with six exercises. It does not replace the ten canonical A1 lesson packets or
their 50 multiple-choice exercises.

The pack references existing `subject-pronouns-etre` grammar and
`a1-etre-speaking` objective records. It reuses the original être lesson's
vocabulary IDs. Its examples practice `je suis`, `tu es`, and `elle est`, with
English translations, usage notes, common mistakes and a recap. Gendered
`étudiant` / `étudiante` written variants are explicit.

The importer validates exactly six formats, stable tile/matching IDs, complete
answer mappings, bounded text, deterministic variants and source metadata.
Reimporting an unchanged version is idempotent. A changed source requires a new
version. Imports are explicit (`--apply`) and transactional. Draft enrichment
refuses to replace an already published grammar topic/linked published lesson.
It records automated provenance, never independent human approval.

`teaching_metadata` holds version, usage, common mistakes, recap, rule reference,
source/license notes and pending review state. Explanations and bilingual
examples use existing `GrammarRule` and `GrammarExample` tables. Objective and
lesson links use the existing mapping tables.

The current explanation preference supports English only. This milestone
honors it and does not imply translations into unimplemented languages.

## Practice categories

| Category | Source and effect |
| --- | --- |
| Vocabulary | Existing enrolled-card `/review` scheduler, with its existing recall grading and due dates |
| Grammar | Authorized exercises with explicit grammar topic references |
| Sentence building | Authorized stable-ID sentence-order exercises |
| Listening | Authorized listening exercises using existing French Piper |
| Review mistakes | Latest unresolved source-exercise errors in the latest 200 attempts, at the current lesson version |

A focused session contains at most 12 exercises from one real lesson, keeping
its source permission and snapshot boundaries intact. It saves attempts and
practice completion; it does not complete the full lesson. Available counts
refer to authorized candidate exercises, potentially across several lessons.
Starting practice selects the first available lesson; further lessons can be
practiced separately.

The server never invents a grammar weakness from a lesson title. Objective
recommendations require explicit IDs and recorded error evidence. Old content
without objective-to-exercise mappings remains eligible for lesson-level review.

## Review and publication

All ten A1 lessons and the new implementation module remain unpublished.
Independent French-language, pedagogical, answer-key, prerequisite and rights
reviews remain separate from automated validation. The source license field
records pending rights review; it is not an assertion of an approved license.
Developer preview requires the existing backend development flag **and** admin
role. There is no browser/localStorage preview bypass.

The public curriculum is therefore intentionally empty for ordinary accounts
until independent review and the existing publication process are completed.
No content was published during this milestone.
