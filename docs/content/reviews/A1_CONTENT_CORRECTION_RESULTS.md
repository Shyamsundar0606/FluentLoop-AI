# A1 content correction results

Date: 2026-11-04. Revision: **1.0.1 → 1.0.2**, all ten existing lessons. This is an AI-assisted technical/editorial correction, **not independent linguistic, pedagogical or licensing approval**. Every lesson remains draft. The prior source is retained at `backend/content/a1/archive/course-1.0.1.json`.

## Lesson-by-lesson review

Each packet was read in full: objectives, English explanations, French vocabulary/definitions, paired examples, grammar, pronunciation guidance, dialogue, five exercises, options, answer keys and recap. Titles, slugs, objective codes, exercise ordering, all 150 options and all 50 correct-option indices are retained.

| Lesson (existing title) | Original issue | Applied correction | Remaining reviewer question |
| --- | --- | --- | --- |
| A1-001 French Sound Patterns and First Words | Exercise 5 asked for a sound pair but offered statements; written activities overstated listening assessment. | Prompt now asks which statement compares /y/ and /u/. Narrowed the first objective to recognizing written guidance. | Check phonetic instructions, approve any future listening examples, and decide whether a full alphabet lesson is needed. |
| A1-002 Greetings and Polite Expressions | Friendly `Ça va ?` appeared in a polite service dialogue without register context. | Added a short explanation of the friendly question and the customer's polite request. French dialogue and keys are unchanged. | Confirm register and regional/natural usage in the café exchange. |
| A1-003 Introducing Yourself | Introduction modeled a different question order from the assessed formal phrase; “two l sounds” in `appelle` was misleading; main had an extra grammar membership. | Consistently teach `Comment vous appelez-vous ?` as a fixed phrase; clarify one /l/ sound. Re-import detaches obsolete lesson-to-topic membership while retaining the shared topic itself. | Check formal/informal phrasing, reduced schwa and an approved pronunciation model. |
| A1-004 Numbers, Age and Basic Questions | `dix` was said to be silent before a pause; age examples used untaught 18/20; written recognition was labeled listening. | Explain standalone /dis/, consonant context and vowel liaison; teach `dix-huit`/`vingt`, `j'ai`/`vous avez` and age `ans` before use. Objective now describes written recognition. Corrected the dialogue summary to describe the actual age exchange. | Review phonetic/regional variants, inversion as a memorized chunk and beginner cognitive load. |
| A1-005 Articles and Noun Gender | `livre` question lacked the intended book meaning; blanket “un has no n” missed liaison; dialogue chunks lacked glosses. | Ask “Which option means a book?”, distinguish feminine pound; contrast `un livre`/`un ami`/`une`, explain elision and gloss the existing dialogue chunks. | Independently solve the revised item and verify gender, liaison and elision explanations. |
| A1-006 Subject Pronouns and Être | `ici`/`professeure` and tu/vous shift were unexplained; speaker B appeared to be both the male student and the teacher addressed as madame. | Gloss existing words and address forms; identify a third speaker C for the unchanged teacher utterance and align context. | Confirm gender/register and whether the six-form reference is sufficiently scaffolded. |
| A1-007 Avoir and Talking About Possessions | Early negation example used untaught `parler`; one sister translation differed from its shared dictionary identity. | Use already taught être in `Je ne suis pas étudiant.`; scaffold negation then `pas de`. Dictionary gloss is `sister`, with an explicit note that `une sœur` means `a sister`. | Review negation scope, exceptions to `pas de`, and whether possession plus negation is too much for one lesson. |
| A1-008 Family and Personal Information | Blanket liaison claim for `mon`; untaught `des` in the dialogue. | Contrast `mon frère`/`mon ami` and `les livres`/`les amis`; explain plural indefinite `des` and definite `les`. | Review liaison, silent/aspirated h, family vocabulary inclusiveness and possessive sequencing. |
| A1-009 Everyday Activities and Common Verbs | Inflected examples were unreachable through vocabulary; regular endings were named without a complete simple mapping. | Explicitly associate `J'habite à Lyon.` with `habiter` and `Nous parlons français.` with `parler`; explain stem/endings and gloss `un peu`. | Check all seven reference paradigms, separate irregular verbs clearly, and review the scope of untaught forms. |
| A1-010 Shopping, Ordering and Everyday Conversations | `voudrais` was incorrectly described as containing `oi` /wa/; price/dialogue chunks were unglossed; written exchange was labeled listening. | Explain `ou` /u/ and `-ais` /ɛ/; keep `je voudrais` as a fixed polite chunk. Gloss price/euro and the existing service phrases; narrow the objective to written recognition. | Approve IPA and regional vowel variation, price vocabulary and any future service audio. |

All recaps and otherwise correct French examples, dialogues and answer options were retained. No external dictionary definitions, recordings or paid materials were imported. These ten lessons are a starter sequence, not proof of complete CEFR A1 coverage.

## Technical corrections

- Article stripping now requires a complete article token or apostrophe. `une table`, `une amie`, `une clé`, `une sœur` and `les parents` no longer become `e table`, `e amie`, `e clé`, `e sœur` and `s parents`. Bare nouns such as `lettre` and `université` are not truncated.
- Known legacy defects are corrected in the existing lesson vocabulary slot, preserving lexical IDs and their sense/card/history references. Existing aliases are not merged or deleted merely to reduce counts. Fresh source has **83 vocabulary occurrences / 77 normalized identities**; upgraded databases can retain historical lexical aliases.
- Every source example now declares its vocabulary associations. Validation rejects unrelated/missing references for current revisions; import reconciles scoped stale associations rather than guessing from substrings or assigning an arbitrary first word.
- Shared lexical notes are selected consistently before import, preventing repeated `avoir`/shared-note timestamp churn. Re-imports report actual counters.
- Source-managed obsolete grammar memberships are detached; shared grammar topics remain. Obsolete source-managed grammar examples can be removed, while frozen learner session data remains unchanged.
- The read-only auditor is shared by the CLI and publisher. It compares metadata, all ten lesson packets, explicit associations, the 50 exercise answers and source provenance. It also checks seven present-tense reference paradigms.

## Supporting language references

These references support specific corrections; they are neither curriculum licenses nor independent reviews. Wording above and in the source is original explanatory text.

- [OQLF: pronunciation of six and dix](https://vitrinelinguistique.oqlf.gouv.qc.ca/23137/la-prononciation/prononciation-des-nombres/prononciation-de-six-et-dix) supports contextual final consonants.
- [Larousse: feminine livre](https://www.larousse.fr/dictionnaires/francais/livre/47532) confirms the alternate weight/currency noun, explaining the ambiguous original item.
- [CNRTL: appeler](https://www.cnrtl.fr/definition/appeler) provides spelling/pronunciation references for the reviewer; no entry text was copied into the lessons.
- [Larousse: vouloir](https://www.larousse.fr/dictionnaires/francais/vouloir/82561) and its [conjugation reference](https://www.larousse.fr/conjugaison/francais/vouloir-conditionnel/9417) support the polite conditional chunk. Detailed phonetic realization remains a specialist review item.

See [publication readiness](../../verification/A1_CURRICULUM_PUBLICATION_READINESS.md) for measured import/test results and [the independent checklist](A1_INDEPENDENT_REVIEW_CHECKLIST.md). No publication command was run against an application database.
