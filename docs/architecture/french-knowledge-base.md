# French knowledge-base architecture

## Database layout

Migration `20261101_0003` adds 31 curriculum and language-data tables in PostgreSQL's existing `public` schema and inserts exactly six rows in `cefr_levels` (A1–C2). The current Alembic chain and authentication tables use the default schema; splitting some related tables across PostgreSQL schemas would require a wider migration and SQLite fixture changes. The implementation therefore uses stable table names and prefixes by domain in code and documentation rather than introducing schemas that the existing migration architecture cannot share consistently.

The migration is additive. It does not alter or delete accounts, sessions, user preferences, or Redis state. The API level identifiers are uppercase, and the existing user-preference identifiers remain lowercase; services normalize the saved value when selecting curriculum. Course rows reference `cefr_levels.code`, while lessons and language content validate against the exact six-level set.

## Entities and relationships

| Domain | Tables | Main relationships |
|---|---|---|
| Level and course structure | `cefr_levels`, `courses`, `units`, `lessons`, `lesson_sections`, `learning_objectives`, `lesson_objectives` | A level has courses; courses have ordered units; units have ordered lessons; lessons have ordered text sections and objective links. |
| Provenance | `content_sources`, `content_import_batches`, `content_provenance` | Batches identify a source and version. Provenance records identify the source, batch, version, automated validation, and review state for a stable content key. |
| Vocabulary | `lexemes`, `word_senses`, `translations`, `example_sentences`, `lexeme_examples`, `pronunciations`, `lesson_vocabulary` | Lexemes are reusable; senses support multiple meanings; translations attach to a sense; examples and pronunciations attach to lexical entries; lessons link lexemes with order and teaching notes. |
| Grammar | `grammar_topics`, `grammar_rules`, `grammar_examples`, `lesson_grammar` | Topics contain rules and examples and may be linked to multiple lessons. |
| Verb and sound references | `verb_lemmas`, `verb_conjugations`, `phonemes` | A verb has one record per mood, tense, person, and number; phonemes store text-only pronunciation guidance. |
| Dialogues and exercises | `dialogues`, `dialogue_turns`, `lesson_dialogues`, `exercises`, `exercise_options`, `exercise_answers` | Lesson-dialogue links ensure read APIs only expose dialogues belonging to published lessons. Exercise options and answer keys are stored separately. |
| Media metadata | `media_assets` | Future media metadata only; no fabricated storage keys or audio files are created. |

Structured JSON is limited to import reports, review metadata, and section-specific metadata. PostgreSQL uses JSONB for these fields; SQLite test fixtures use JSON.

## Content retrieval and publication

All learner curriculum routes require an authenticated session. Level, course, unit, lesson, vocabulary, grammar, conjugation, and dialogue responses are typed and bounded with `limit`/`offset` where they return collections. Explicit `?level=A1` browsing is independent of `user_preferences.current_level`; omitting the parameter resolves the signed-in learner's saved level without modifying it.

The public query path requires the course, unit, and lesson to be `published`. A published child cannot bypass a draft parent. Vocabulary, grammar, dialogues, and verb references are exposed only when linked to a published lesson. Exercise responses serialize option text and order only; they never serialize `is_correct`, `accepted_answer`, or answer explanations.

Content import is a trusted local process, not an API. It validates source content, records provenance, and upserts records by natural identity. It leaves all courses, units, and lessons in draft status. A separate local publication command requires a complete administrator-prepared review record covering every lesson's French, pedagogy/sequence, and answer keys, as well as a separate licensing/attribution approval. The record is bound to the source version and digest. The current A1 source has not received these independent human reviews, so it remains unpublished.

## Linguistic normalization

Lexeme identity includes NFKC-normalized, case-folded lemma, part of speech, and grammatical gender. Accents are preserved in display lemmas and are not stripped from normalized search keys. The initial search supports a bounded substring query; `é` and `e` are distinct. A future accent-insensitive search should add and test a separate normalized key rather than altering the learner-facing spelling.

## Current content state

The checked-in A1 JSON source contains ten AI-assisted draft lessons, 83 source vocabulary entries, and 50 multiple-choice exercises. The importer reuses lexemes across lessons, so persisted unique lexeme count is lower than the source-entry count. Five additional course outlines and their planned units/objectives are draft-only. Source provenance identifies the content as AI-assisted and asserts no publication license; rights and attribution review remain pending. No audio, learner progress, grading, AI tutoring, or speech processing is included.
