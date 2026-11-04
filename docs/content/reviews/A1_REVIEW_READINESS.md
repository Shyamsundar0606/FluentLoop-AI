# A1 review readiness — 3 November 2026

## Decision and scope

**All ten lessons remain draft. No independent human approval or publication is claimed.** This packet combines automated integrity checks, an AI-assisted editorial inspection of every lesson, and references for specific findings. It does not replace a qualified French-language, pedagogy, exercise, or rights reviewer.

[Concrete correction proposals](A1_PROPOSED_CORRECTIONS.md) provide suggested replacement wording, answer-key impacts and a technical reconciliation plan for review. They have not been applied to the source or deployed drafts.

Source: [course.json](../../../backend/content/a1/course.json), version **1.0.1**. The earlier [A1 curriculum review](A1_CURRICULUM_REVIEW.md) is historical; the current deployed-state findings below take precedence for readiness.

- Raw source file SHA-256: `c8a47a578c42d4cd6d45c4f0f6827cf96dd0150a344c161b64b90ddabe1ec41d`.
- Canonical source SHA-256 used by the existing publication gate: `8c8fb60c5bbfc25a2dca0acbbcae9c540e20330582c66438c5c25eb8519ef53c`.
- Importer SHA-256: `45fa0d3454a94a402fafe8834ef2f3467e79e4640d56233d30fd45e6ac94ad20`. The importer contains verb and phoneme reference content outside the JSON; reviewers must inspect both.
- Both databases: one A1 course, five draft units, **10 draft lessons, 0 published**. No A2–C2 lessons were created.
- All lesson provenance remains automated-checked, without independent-human-review attestation. The existing approval template still has every review pending.

## Automated inspection

[Read-only auditor](../../../backend/scripts/a1_review_audit.py), [main database evidence](../../verification/A1_REVIEW_AUDIT_MAIN.json), [preview evidence](../../verification/A1_REVIEW_AUDIT_PREVIEW.json).

The auditor validates the source schema and compares deployed titles, descriptions, versions, unit/lesson order, introductions, pronunciation sections, recaps, objectives, ordered vocabulary, gender, definitions, English translations, IPA, vocabulary-linked examples, grammar topics/rules/examples, dialogue speaker order and translations, exercise prompts/options/correct flags/accepted normalized answers, and lesson provenance. All **50 exercise keys** match the imported source structurally. Structural matching cannot establish whether a question has only one linguistically valid answer; A1-005 demonstrates this limitation.

The source contains 83 lesson-vocabulary occurrences representing 78 normalized lexical identities, and five exercises per lesson. The evidence also exports seven verbs with 42 present-tense forms and six phoneme symbols. Forms and pronunciation descriptions were inspected in the source/importer, but these exports are not an independent phonetics certification.

**Deployed consistency: main 8/10 lessons pass, preview 9/10 pass.** These are comparisons to the draft source, not quality scores. Both aggregate integrity results are intentionally **false**:

1. Main A1-003 links an additional `basic-sentence-order` grammar topic alongside the expected `introducing-yourself`. Preview matches the source. The topic must be reconciled deliberately, with existing lesson/progress compatibility considered; it was not removed here.
2. In both databases A1-009's `J'habite à Lyon.` and `Nous parlons français.` exist as sentences but have **zero LexemeExample links**. Vocabulary-based lesson retrieval cannot reach them. The current importer also reproduces this omission in a clean isolated test. Record a separate importer/link correction, then repeat the audit; this task leaves deployed draft content untouched.

A regression test constructs a consistent disposable fixture, verifies a clean comparison, then changes a correct-option flag and confirms the auditor reports the drift using only SELECT statements. Production auditing uses a PostgreSQL read-only transaction and never imports, repairs, or publishes content.

## Lesson-by-lesson disposition

**Additional finding, 4 November 2026 (Milestone 07 preview testing):** the existing noun importer matches `un` before `une` and accepts article prefixes without a word boundary. Five source occurrences currently become malformed stored lemmas: `une table → e table`, `une amie → e amie`, `une clé → e clé`, `une sœur → e sœur`, and `les parents → s parents`. See [the read-only diagnostic](../../verification/MILESTONE_07_CONTENT_LIMITATIONS.json). This explains why source-to-database equality against the same importer can pass while linguistic data is still wrong. No source, importer or deployed lexical record was repaired by Milestone 07. Correct the importer and reconcile stable lexical IDs/references through a separately reviewed content revision before publication. Preview cards remain explicitly unreviewed; ordinary learners cannot access these drafts.

“Review packet ready” means an independent reviewer can begin with the current technical packet. It never means approved for learners. “Correction recommended” means the listed editorial or data issue should be addressed and rechecked before final sign-off. Every row additionally requires rights approval and all three lesson approvals.

| Lesson | Vocabulary / exercises | Main / preview DB comparison | Readiness and principal findings |
|---|---:|---|---|
| A1-001 French Sound Patterns and First Words | 8 / 5 | pass / pass | **Correction recommended.** Basic greetings and /y/–/u/ distinction suit beginners. Exercise 5 asks for a sound pair but offers statements rather than pairs. Rewrite the question or options. Listening discrimination is an objective, yet exercises are written; a reviewer should require an actual reviewed listening task or narrow that objective. |
| A1-002 Greetings and Polite Phrases | 8 / 5 | pass / pass | **Review packet ready with notes.** Greetings, thanks, please and farewell translations/keys appear coherent in this AI inspection. Review formal/informal transitions: the dialogue combines `Bonjour madame` with `Ça va`. Ensure register and when to use each expression are explicit. |
| A1-003 Introducing Yourself | 8 / 5 | **fail** / pass | **Correction recommended.** Name and introduction expressions fit A1 as fixed chunks; formal `Comment vous appelez-vous ?` needs a simple model. Pronunciation guidance referring to “two l sounds” in `appelle` is misleading: two written letters do not imply two successive /l/ sounds. Explain the spelling/vowel and a single /l/ with an expert-approved model. Reconcile the extra main-DB grammar topic. |
| A1-004 Numbers, Age and Simple Questions | 8 / 5 | pass / pass | **Correction recommended, high priority.** The pronunciation section incorrectly says the final consonant of `dix` is usually silent before a pause. Standalone/final `dix` is /dis/; contextual forms differ. Grammar covers 0–10 while age examples use 18/20; introduce these numbers or label them explicitly as fixed examples. Avoir-based age keys are structurally consistent. |
| A1-005 Articles, Gender and Simple Nouns | 8 / 5 | pass / pass | **Correction recommended.** Exercise 1 asks which article belongs with `livre` without specifying “book.” `Un livre` is the intended book answer, but feminine `une livre` is also a valid French noun meaning pound. Add the intended meaning. Qualify the nasal-vowel statement about `un`: a following vowel/silent h can trigger liaison. Make clear that `l’` does not visibly reveal gender. |
| A1-006 Subject Pronouns and Être | 9 / 5 | pass / pass | **Review packet ready with notes.** The six present forms of être and written agreement examples appear consistent. Gloss new dialogue words such as `professeure` and `ici`; explain shifts between `tu` and `vous`. Check whether all genders and pronoun choices are sufficiently modeled for a beginner. |
| A1-007 Avoir and Everyday Possessions | 8 / 5 | pass / pass | **Correction recommended.** Resolve the imported `e clé` and `e sœur` noun artifacts noted above. Present-tense possession and negation/`pas de` appear coherent in the source inspection. Review cognitive load from introducing negation and article changes together. `Je ne parle pas` precedes the regular-verb lesson: teach it explicitly as a chunk or model the already known verb first. |
| A1-008 Family and Personal Information | 10 / 5 | pass / pass | **Correction recommended.** Possessive guidance and keys are broadly coherent, but the pronunciation claim that final n in `mon` normally links to the following noun is overgeneralized. Contrast `mon ami` with `mon frère`, identifying the vowel/silent-h condition. Introduce the dialogue's plural article `des` before assessment. |
| A1-009 Everyday Activities and Regular -er Verbs | 8 / 5 | **fail / fail** | **Technical correction required.** Link the two missing examples described above. Regular -er forms and written keys appear consistent; clearly separate irregular `aller`/`faire` from that pattern. Residence was already used as a fixed introduction earlier; explicitly connect that chunk to the new rule. Gloss `un peu` and check dialogue vocabulary coverage. |
| A1-010 Shopping and Everyday Requests | 8 / 5 | pass / pass | **Correction recommended, high priority.** The pronunciation instruction about `oi` in `voudrais` is wrong: the word contains no `oi`. It contains `ou` /u/ and a final `-ais` vowel /ɛ/. Have a reviewer approve a full pronunciation example. `Je voudrais` is appropriate as a polite fixed chunk; avoid requiring the complete conditional paradigm at this point. Teach price/euro vocabulary before price exercises. |

With the additional importer findings, two packets (002, 006) can begin independent review with scaffold notes; eight have specific correction recommendations or technical blockers. All ten can be inspected now, but **none can be published now**. These classifications are editorial triage, not independent approval. This supersedes the earlier three/seven triage recorded before Milestone 07 testing.

## Sequencing and completeness

The progression sounds/first words → greetings → introductions → numbers/age → articles/gender → pronouns/être → avoir/negation → family/possessives → activities/-er → shopping has a plausible beginner arc. Risks are early unglossed chunks, age numbers beyond the taught range, several concepts introduced together, and written assessment of listening objectives. A reviewer should check every objective against an explanation, a modeled example, practice and an answer explanation. Ten lessons are not evidence of complete CEFR A1 coverage or an accredited A1 course.

Source translations, definitions, grammar explanations, paired examples and dialogue turns were read across all ten lessons. No claim is made that automated equality or an AI reading proves every translation, IPA, register choice or distractor correct. Reviewers should use the original JSON and authorized preview, not only this summary.

## Provenance and licensing blockers

The actual metadata says `ai_assisted_draft`, has no source URL, uses license text `Unreviewed AI-assisted draft; no publication license asserted`, and records attribution/rights review as pending. An import digest proves the imported version, not permission to publish it. There is no documentary rights approval in the current packet.

A rights reviewer must establish the origin of any adapted vocabulary definitions, examples, dialogues, exercise wording, IPA/reference content and recordings, identify applicable terms, and record attribution obligations and evidence. Dictionaries linked below support specific language observations; this task did not copy their entries into the curriculum or grant any rights to their content. Piper voice/dataset licensing is a separate speech-system attribution issue and does not clear lesson-content rights.

## Independent reviewer checklist — unfilled

Reviewer name: __________  Role/qualifications: __________  Independence attestation: __________
Version + canonical SHA reviewed: __________  Date/time with timezone: __________
Evidence location and written decision: __________

For **each of A1-001 through A1-010**, record separate decisions for:

- [ ] French-language correctness: accents, spelling, gender, agreement, verb forms, IPA, pronunciation, liaison, register, natural examples/dialogues and faithful English translations; address each finding above.
- [ ] Pedagogy and sequence: A1 fit, prerequisites, glossed vocabulary, manageable concept load, explicit instruction before use, objective/practice/assessment alignment, listening needs and accessible examples.
- [ ] Exercise answers: independently solve all five items before viewing keys; verify exactly one intended valid option, acceptable answer normalization, distractor fairness, feedback accuracy and no cues relying on untaught content.
- [ ] Technical review: repeat source-to-DB audit after approved corrections, verify A1-003 and A1-009 reconciliation, and inspect reference data from the exact importer version.

Course-wide rights review:

- [ ] Establish source ownership/permissions and compatibility for all included material and any added audio; provide evidence references and required attribution.
- [ ] Verify source metadata, license and attribution accurately describe the approved material, not a placeholder.
- [ ] Keep every status draft while any review is pending, rejected or version-mismatched.

Use a **copy** of [the existing publication review template](A1_PUBLICATION_REVIEW_TEMPLATE.json). Populate genuine independent language, pedagogy and exercise approvals for all ten unique lesson slugs, plus course-wide license/attribution approval, identified reviewers, evidence references and timezone-aware dates. Bind approvals to the final canonical source digest/version. If content changes, invalidate the old review and repeat applicable checks. Only an authorized operator should then use the existing publisher. **No publisher was run and no approval template was filled by this task.**

## Language references for the findings

- [Académie française: dix](https://www.dictionnaire-academie.fr/article/A9D2877) and [OQLF: pronunciation of six and dix](https://vitrinelinguistique.oqlf.gouv.qc.ca/23137/la-prononciation/prononciation-des-nombres/prononciation-de-six-et-dix): context-dependent final consonant, supporting the A1-004 correction.
- [Larousse: livre, feminine noun](https://www.larousse.fr/dictionnaires/francais/livre/47532): the alternate meaning makes A1-005's unqualified question ambiguous.
- [CNRS LGIDF: La personne](https://lgidf.cnrs.fr/sites/lgidf.cnrs.fr/files/images/LGIDF.LA%20PERSONNE.DEF..pdf): possessive determiners and liaison before a following vowel, supporting the A1-008 qualification.
- [Larousse: appeler](https://www.larousse.fr/dictionnaires/francais/appeler/4669): spelling/conjugation reference for the A1-003 reviewer.
- [Académie française: vouloir](https://www.dictionnaire-academie.fr/article/A9V1230): polite conditional usage for the A1-010 reviewer. The `oi` finding also follows directly from the letters in the lesson's own `voudrais` example.
