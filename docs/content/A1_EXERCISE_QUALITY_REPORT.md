# A1 exercise quality report

The A1 grammar supplement release `0.1.0` adds 25 exercises across 12 new
draft lessons. The existing six-format être fixture supplies practice for the
thirteenth topic. Each added exercise belongs to one grammar topic and one
objective already linked to the relevant original lesson.

| Format | New items | Validation and grading |
| --- | ---: | --- |
| Multiple choice | 12 | Unique normalized choices and one in-range key |
| Fill in the blank | 3 | Explicit deterministic keys |
| Sentence ordering | 2 | Stable tile IDs, full permutations and a reconstructed feedback sentence |
| Word matching | 2 | Stable item IDs and complete one-to-one mappings |
| Listening comprehension | 5 | French script and selected translation agree with the paired teaching example |
| Short written response | 1 | Explicit expected sentence, with existing punctuation and apostrophe normalization |

The source uses NFC and rejects invalid references or duplicate topic and
exercise keys. The existing grader handles Unicode composition and straight
or curly apostrophes. It requires meaningful accents. For example, the
existing être fixture expects **étudiant** or **étudiante** with **é**.
Reviewers should test both keyboard entry and paste on a French keyboard and
a keyboard without a direct **é** key.

The 50 original answer indices and six existing fixture exercises retain
their identities and meaning. The new release has its own course and lesson
slugs and provenance keys. Each installed release is immutable. A change to
answer logic requires a new release with new exercise identities, while saved
sessions continue to use their frozen answers.

Practice uses the existing session engine. Topic-focused sessions can include
any linked format. Result feedback and mistake review use actual attempts.
The existing adaptive service can recommend a review using the linked
objective and the recorded error IDs. Vocabulary uses the existing senses
and review schedule.

Automated validation checks structural consistency. A qualified reviewer
must still judge linguistic accuracy, listening intelligibility, plausible
distractors, CEFR fit and licensing. The [independent review record](A1_GRAMMAR_CONTENT_REVIEW.md#independent-review-record) lists the five pending checks.
