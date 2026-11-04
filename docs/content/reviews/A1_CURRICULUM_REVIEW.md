# A1 Curriculum Prepublication Review

## Review status and limits

This is an AI-assisted editorial and data-integrity review of the ten A1 draft lessons. It is not independent human French-language review, pedagogical approval, or legal advice. No lesson is approved for publication. The source remains `ai_assisted_draft`, states that no publication license is asserted, and the review manifest remains pending.

- Source: `backend/content/a1/course.json`, version `1.0.1`
- Source SHA-256: `8c8fb60c5bbfc25a2dca0acbbcae9c540e20330582c66438c5c25eb8519ef53c`
- Scope: French vocabulary and translations, noun gender, definitions, examples, grammar explanations, conjugations, pronunciation references, dialogue text and translations, exercise prompts/options/answers, sequencing, source/database consistency, and provenance.

## Audit results

- Schema validation passed for 10 lessons, 83 vocabulary entries, 50 exercises, and five planned A2-C2 course outlines.
- The 83 vocabulary occurrences resolve to 78 normalized lexical identities. Five repeated occurrences have consistent translations and French definitions. No duplicate exercise prompts or example sentences were found.
- Database cross-reference checks verified vocabulary links, lemma and gender identity, definitions, English translations, IPA references, examples, grammar rules and examples, dialogue turns, exercise prompts/options, correct-option flags, and accepted answers against the source.
- All 50 answer keys were checked against PostgreSQL exercise options and accepted-answer records directly, not through learner-facing APIs. Correct option positions are distributed 17/17/16 among indices 0/1/2.
- The imported version has 10 draft lessons and zero published lessons. Provenance is automated-only; it does not claim independent human review.
- A source/database comparison found one stale `Tu as un téléphone ?` grammar example from version 1.0.0 attached to lesson 4's simple-question rule. The import reconciliation was corrected to remove obsolete examples only for source-managed rules while retaining the union of examples still present in the current source. Reapplying version 1.0.1 removed that single stale row; the current rule now matches the source.
- Licensing remains unresolved. No publication license is asserted for the AI-assisted source, so all lessons are blocked regardless of the editorial findings below.

## Lesson-by-lesson review

| Lesson | Sequence and coverage | AI-pass findings and changes applied | Readiness |
|---|---|---|---|
| A1-001 — French Sound Patterns and First Words | First sounds, first words, greeting, spelling-to-sound awareness | Aligned the title/objectives with the sound content and clarified that French final /ʁ/ is produced at the back of the mouth. The u /y/ versus oo /u/ contrast is stated explicitly. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-002 — Greetings and Polite Expressions | Greetings, register, and polite requests | No specific correction was identified in this AI pass. Register and polite/informal variants still require independent review. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-003 — Introducing Yourself | Names, identity words, and formal address | Removed an unsupported country objective and grammar that was ahead of the lesson sequence. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-004 — Numbers, Age and Basic Questions | Numbers zero to ten, age with *avoir*, formal questions | Completed the number sequence through dix and removed premature informal *tu* usage from this stage. Reconciled a stale prior-version grammar example in PostgreSQL. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-005 — Articles and Noun Gender | Articles and gendered nouns | Corrected the explanation of the nasal sound in *un*. Noun gender must still be confirmed by an independent French reviewer. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-006 — Subject Pronouns and Être | Subject pronouns and present-tense *être* | Added *étudiante* and clarified the pronunciation note for *suis*. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-007 — Avoir and Talking About Possessions | Present-tense *avoir* and possessions | Added the explanation that *de* follows negation in the relevant construction. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-008 — Family and Personal Information | Family vocabulary and possessives | Added *mes* and *ta* so the stated possessive coverage is represented in the lesson. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-009 — Everyday Activities and Common Verbs | Everyday routines and common present-tense verbs | Narrowed the objective to match the actual lesson coverage. | Blocked: independent language, pedagogy, and answer-key review pending. |
| A1-010 — Shopping, Ordering and Everyday Conversations | Polite requests and a short service exchange | Improved the *croissant* and *carte* definitions/translations. The service dialogue and register need independent review. | Blocked: independent language, pedagogy, and answer-key review pending. |

## Conjugation audit

The source/database checks cover 42 present-indicative forms. Automated tests compare all six person/number forms for each verb:

| Infinitive | je | tu | il/elle | nous | vous | ils/elles |
|---|---|---|---|---|---|---|
| *être* | suis | es | est | sommes | êtes | sont |
| *avoir* | ai | as | a | avons | avez | ont |
| *aller* | vais | vas | va | allons | allez | vont |
| *faire* | fais | fais | fait | faisons | faites | font |
| *parler* | parle | parles | parle | parlons | parlez | parlent |
| *habiter* | habite | habites | habite | habitons | habitez | habitent |
| *aimer* | aime | aimes | aime | aimons | aimez | aiment |

## Exercise answer-key audit

The following are the keyed correct responses in exercise order (1-5) for each lesson. Tests and the PostgreSQL audit compare each answer with its source options, database `is_correct` value, and accepted-answer record. These keys are for review and are not exposed by learner APIs.

- **A1-001:** bonjour; thank you; oui; salut; French u /y/ and English oo /u/ are different sounds.
- **A1-002:** bonsoir; s'il vous plaît; goodbye; Ça va ?; s'il te plaît.
- **A1-003:** Je m'appelle Léa.; le prénom; Comment vous appelez-vous ?; pleased to meet you; vous.
- **A1-004:** avoir; two; Quel âge avez-vous ?; ai; ten.
- **A1-005:** un livre; une table; le; la maison; learn a French noun with its article.
- **A1-006:** suis; tu; êtes; nous; Elle est ici.
- **A1-007:** ai; a; a key; avec; I have a telephone.
- **A1-008:** mother; mon frère; ma sœur; mes parents; ta.
- **A1-009:** to live; parlons; aller; some written endings are silent; today.
- **A1-010:** Je voudrais un croissant.; how much/how many; the bill; s'il vous plaît; a croissant.

## Publication decision

- **Publication-ready:** none.
- **AI-pass corrections applied, with independent review still required:** A1-001 and A1-003 through A1-010.
- **No specific correction identified by this AI pass, with independent review still required:** A1-002.
- **Blocked pending independent review:** all ten lessons. Each still needs independent French-language, pedagogy/sequence, and answer-key approval. The source also needs a separate licensing/attribution decision before any publication.

Do not treat this report or automated tests as human approval. Keep the publication manifest pending and all lessons unpublished until the required independent reviews and license decision are recorded.
