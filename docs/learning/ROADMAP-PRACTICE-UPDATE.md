# A1–C2 roadmap practice update

The immutable pre-import manifest retains its historical authorization state. The
[import receipt](../../backend/content/roadmap/manifest/IMPORT-RECEIPT-20261123.json)
records the subsequent authorized transaction. Main totals are 317 lessons, 892
scored exercises and 118 open tasks. Five earlier writing bridges remain staged.

## Final technical validation — 23 November 2026

**Passed and imported as unpublished personal drafts after direct authorization.** The exact active batch is pinned in
[the import manifest](../../backend/content/roadmap/manifest/IMPORT-MANIFEST-20261123.json):
12 releases, 136 lessons, 272 scored exercises and 68 open writing/speaking tasks.
All 136 lesson slugs, exercise keys, authored prerequisites and source file hashes
are listed. The [review ledger](../../backend/content/roadmap/manifest/LESSON-REVIEW-20261123.json)
retains qualified-human-review and calibration flags for every lesson.

- Fresh consistent backup and exact-batch PostgreSQL restore/import passed.
  Main 181 + 136 = 317 lessons; 620 + 272 = 892 exercises; 50 + 68 = 118 open tasks.
  The earlier five writing bridges and superseded drafts are excluded.
- All 272 keys/distractors, idempotency, foreign keys, 124 within-release prerequisite
  edges and retention of prior rows passed. Main/M08 before/after signatures matched.
- All 68 scripts generated bounded non-silent WAV files and passed headless Chromium
  decoding/playback: normal-speed start, accelerated completion, output muted.
  [Audio evidence](../../backend/content/roadmap/manifest/AUDIO-VALIDATION-20261123.json)
  is automated evidence, not physical speaker acceptance or human phonetic approval.
- Fresh 10 targeted backend cases, 68 audio browser cases, ESLint and TypeScript passed.
  The unchanged-batch full backend checkpoint is 394 passed/16 optional skipped.
- All validation-owned infrastructure and speech services shut down gracefully.
  The exact main import subsequently succeeded; no publication, commit, push or deployment occurred.

No technical blocker was found. Qualified independent French/pedagogy/phonetic
review and empirical CEFR calibration remain pending for all 136 lessons. These
limits remain separate from technical import readiness. Selected constructions
were reference-checked against [OQLF](https://vitrinelinguistique.oqlf.gouv.qc.ca/24238/la-grammaire/le-verbe/modes/subjonctif/subjonctif-ou-indicatif-apres-les-subordonnants-composes),
[Académie française](https://www.dictionnaire-academie.fr/article/QDL039) and
[the Académie's inversion guidance](https://www.dictionnaire-academie.fr/article/QR_0560).

Supplementary roadmap practice; existing52-module map, prior 181 lessons and five staged bridges preserved.

**Imported: 136 lessons, 272 scored exercises and 68 writing/speaking tasks across 68 roadmap topics. All remain unpublished.**

Every topic has a rule/model, original fictional reading, contextual expressions, a listening script and open transfer. All six supported exercise formats occur across the batch.

The crosswalk below is a thematic reference, not a replacement learning order. Follow the roadmap preparation chain for these topics. Existing module IDs and stored progress are unchanged. Across release boundaries prerequisites are recommendations; the importer enforces only authored within-release links.

| Topic | Existing module | New scored / transfer | Reading words / script characters |
|---|---|---:|---:|
| a1-roadmap-01 French basics | a1-01 | 4 / 1 | 31 / 119 |
| a1-roadmap-02 Greetings | a1-01 | 4 / 1 | 27 / 122 |
| a1-roadmap-03 Personal information | a1-02 | 4 / 1 | 30 / 95 |
| a1-roadmap-04 Numbers and time | a1-02 | 4 / 1 | 31 / 135 |
| a1-roadmap-05 Nouns and articles | a1-03 | 4 / 1 | 27 / 115 |
| a1-roadmap-06 Basic verbs | a1-03 | 4 / 1 | 26 / 98 |
| a1-roadmap-07 Sentence building | a1-03 | 4 / 1 | 31 / 120 |
| a1-roadmap-08 Everyday activities | a1-05 | 4 / 1 | 28 / 102 |
| a1-roadmap-09 Family and people | a1-04 | 4 / 1 | 30 / 109 |
| a1-roadmap-10 Food and shopping | a1-06 | 4 / 1 | 30 / 117 |
| a1-roadmap-11 Places and directions | a1-07 | 4 / 1 | 30 / 142 |
| a1-roadmap-12 Essential conversation | a1-09 | 4 / 1 | 25 / 133 |
| a2-roadmap-01 A1 consolidation | a2-08 | 4 / 1 | 37 / 129 |
| a2-roadmap-02 Past experiences | a2-02 | 4 / 1 | 37 / 117 |
| a2-roadmap-03 Describing the past | a2-02 | 4 / 1 | 34 / 122 |
| a2-roadmap-04 Future plans | a2-01 | 4 / 1 | 35 / 148 |
| a2-roadmap-05 Modal expressions | a2-01 | 4 / 1 | 32 / 126 |
| a2-roadmap-06 Objects and pronouns | a2-04 | 4 / 1 | 36 / 124 |
| a2-roadmap-07 Comparison | a2-04 | 4 / 1 | 38 / 155 |
| a2-roadmap-08 Connecting ideas | a2-06 | 4 / 1 | 37 / 138 |
| a2-roadmap-09 Health and appointments | a2-05 | 4 / 1 | 35 / 127 |
| a2-roadmap-10 Work and education | a2-01 | 4 / 1 | 35 / 148 |
| a2-roadmap-11 Housing and administration | a2-01 | 4 / 1 | 34 / 134 |
| a2-roadmap-12 Social communication | a2-06 | 4 / 1 | 34 / 132 |
| b1-roadmap-01 Narrative skills | b1-01 | 4 / 1 | 50 / 141 |
| b1-roadmap-02 Future and possibilities | b1-04 | 4 / 1 | 40 / 133 |
| b1-roadmap-03 Hypothetical situations | b1-04 | 4 / 1 | 47 / 155 |
| b1-roadmap-04 Subjunctive introduction | b1-03 | 4 / 1 | 46 / 159 |
| b1-roadmap-05 Complex pronouns | b1-05 | 4 / 1 | 48 / 125 |
| b1-roadmap-06 Passive constructions | b1-05 | 4 / 1 | 49 / 130 |
| b1-roadmap-07 Reported speech | b1-06 | 4 / 1 | 47 / 141 |
| b1-roadmap-08 Opinions and arguments | b1-02 | 4 / 1 | 47 / 147 |
| b1-roadmap-09 Society and culture | b1-06 | 4 / 1 | 49 / 156 |
| b1-roadmap-10 Workplace communication | b1-07 | 4 / 1 | 50 / 145 |
| b1-roadmap-11 Media comprehension | b1-06 | 4 / 1 | 51 / 174 |
| b1-roadmap-12 Independent expression | b1-08 | 4 / 1 | 54 / 155 |
| b2-roadmap-01 Advanced tense control | b2-04 | 4 / 1 | 82 / 176 |
| b2-roadmap-02 Subjunctive mastery | b2-01 | 4 / 1 | 80 / 169 |
| b2-roadmap-03 Complex hypotheses | b2-04 | 4 / 1 | 72 / 168 |
| b2-roadmap-04 Advanced relative clauses | b2-03 | 4 / 1 | 74 / 156 |
| b2-roadmap-05 Discourse connectors | b2-03 | 4 / 1 | 74 / 187 |
| b2-roadmap-06 Argumentative writing | b2-06 | 4 / 1 | 82 / 175 |
| b2-roadmap-07 Formal communication | b2-02 | 4 / 1 | 72 / 198 |
| b2-roadmap-08 Media analysis | b2-05 | 4 / 1 | 78 / 164 |
| b2-roadmap-09 Professional French | b2-07 | 4 / 1 | 81 / 176 |
| b2-roadmap-10 Abstract discussions | b2-01 | 4 / 1 | 82 / 193 |
| b2-roadmap-11 Listening fluency | b2-05 | 4 / 1 | 85 / 221 |
| b2-roadmap-12 DELF B2 practice | b2-08 | 4 / 1 | 86 / 216 |
| c1-roadmap-01 Advanced grammar | c1-04 | 4 / 1 | 106 / 201 |
| c1-roadmap-02 Sophisticated vocabulary | c1-04 | 4 / 1 | 103 / 194 |
| c1-roadmap-03 Register and style | c1-04 | 4 / 1 | 107 / 187 |
| c1-roadmap-04 Idiomatic language | c1-04 | 4 / 1 | 98 / 166 |
| c1-roadmap-05 Argumentation | c1-06 | 4 / 1 | 101 / 184 |
| c1-roadmap-06 Academic writing | c1-06 | 4 / 1 | 106 / 186 |
| c1-roadmap-07 Advanced listening | c1-05 | 4 / 1 | 100 / 230 |
| c1-roadmap-08 Professional fluency | c1-02 | 4 / 1 | 103 / 230 |
| c1-roadmap-09 Literary and cultural analysis | c1-04 | 4 / 1 | 100 / 214 |
| c1-roadmap-10 DALF C1 preparation | c1-08 | 4 / 1 | 103 / 188 |
| c2-roadmap-01 Complete grammar mastery | c2-02 | 4 / 1 | 119 / 228 |
| c2-roadmap-02 Precision in vocabulary | c2-02 | 4 / 1 | 111 / 186 |
| c2-roadmap-03 Literary French | c2-04 | 4 / 1 | 121 / 199 |
| c2-roadmap-04 Rhetoric and persuasion | c2-01 | 4 / 1 | 114 / 207 |
| c2-roadmap-05 Cultural understanding | c2-03 | 4 / 1 | 116 / 211 |
| c2-roadmap-06 Advanced written expression | c2-07 | 4 / 1 | 111 / 171 |
| c2-roadmap-07 High-level listening | c2-05 | 4 / 1 | 115 / 249 |
| c2-roadmap-08 Professional specialization | c2-04 | 4 / 1 | 104 / 204 |
| c2-roadmap-09 Spontaneous communication | c2-06 | 4 / 1 | 105 / 224 |
| c2-roadmap-10 DALF C2 preparation | c2-08 | 4 / 1 | 113 / 237 |

## Review limits

Roadmap grouping and estimated hours are planning suggestions, not official CEFR grammar requirements or guarantees. Garbled vocabulary graph not converted into invented targets. No account-level change.

These are targeted practice sets, not complete modules with 10–20 independently reviewed new words each. The three expressions are taught in context; no new shared SRS glossary entries are authored. Advanced grammar choices sample supported form control; advanced reading/transfer target scope, attribution and nuance. Neither is evidence of mastery.

DELF/DALF topics contain original preparatory activities, not copied examination papers or full official-format mock tests. Study hours, lexical breadth, natural listening and spontaneous productive performance are not calibrated by these exercises.

Main remains181 unpublished lessons/620 scored exercises/50 open task lessons. With the earlier five writing bridges, future staged inventory is 141 lessons / 272 scored exercises/73 open tasks. A fresh reviewed backup and successful import rehearsal are required before separately authorizing any main import.

Qualified independent French, pedagogy, pronunciation and productive-task review remain pending.

## References

- https://www.coe.int/en/web/common-european-framework-reference-languages/reference-level-descriptions
- https://www.france-education-international.fr/en/diplome/delf-tout-public/niveau-b2
- https://www.france-education-international.fr/diplome/dalf

## Earlier verification checkpoint (before final audio validation)

- Full backend: **394 passed, 16 optional tests skipped**, two dependency deprecation warnings.
- In-memory SQLite and a new disposable PostgreSQL restore: **passed**.
- All 272 correct keys and every alternative choice/valid structured wrong answer checked; idempotency, foreign keys, prerequisites and prior-row preservation passed.
- All 68 topic titles and their order match the supplied roadmap.
- Main 181/620 and historical M08: every read-only before/after table signature matched.
- Only owner-authorized PostgreSQL/Redis/Mailpit infrastructure started; then gracefully stopped, including the owned Docker Desktop. No app, AI or speech startup.
- Audio-format and 600-character bounds validated; actual synthesis/playback of these 68 new scripts remains pending.
- No main import, curriculum publication, commit or GitHub push.
