# A1–C2 roadmap practice — imported personal drafts

This active batch follows all 68 topics in the owner's supplied roadmap:
**136 lessons,272 scored exercises and68 open writing/speaking transfer tasks**.
There are12 versioned release packs, all `0.11.x`, imported into the personal database after direct authorization.

| Level | Topics | Practice + transfer lessons | Scored exercises | Open tasks |
|---|---:|---:|---:|---:|
| A1 | 12 | 24 | 48 | 12 |
| A2 | 12 | 24 | 48 | 12 |
| B1 | 12 | 24 | 48 | 12 |
| B2 | 12 | 24 | 48 | 12 |
| C1 | 10 | 20 | 40 | 10 |
| C2 | 10 | 20 | 40 | 10 |

Each topic has an original fictional reading, a rule and translated model,
three contextual expressions, four scored activities, a listening script and an
open writing/speaking transfer with revision criteria. Across the batch, activities
use multiple choice, short answer, fill blank, sentence order, matching and listening.
B2–C2 form/meaning choices use grammatically formed changes in scope, certainty,
attribution or commitment; advanced difficulty is not reduced to spelling errors.

Use `backend/scripts/build_roadmap_practice.py` to reproduce the immutable active
release files. Use `backend/scripts/validate_roadmap_practice.py` to rehearse in
in-memory SQLite only. The manifest retains the recorded validation; repeated
validation should save a new dated report rather than overwrite that evidence.

Initial `0.10.x` drafts and their first rehearsal are retained in `review-history/`.
They were superseded during review, were never imported to main, and are **not
part of the active batch**. Do not recursively collect historical JSON as imports.

The [crosswalk](../../../docs/learning/ROADMAP-PRACTICE-UPDATE.md) links every
roadmap topic to an existing module and is integrated into the existing 52-module live learning
map. Within a release, practice follows the previous transfer and each transfer
requires its practice. Across releases/levels, the documented preparation chain
is a recommendation, not a new enforced database prerequisite.

SQLite and disposable PostgreSQL import/idempotency/foreign keys and every
correct/wrong answer key passed. All 186 prior source lessons and their rows were
preserved in rehearsal. Main and M08 read-only table signatures matched before
and after. The owner separately authorized a bounded infrastructure window;
the existing guard passed before only PostgreSQL/Redis/Mailpit were started.
Those owned services were then gracefully stopped. No main import occurred.
The separately authorized final validation also synthesized all68 listening
scripts with the existing private Piper worker. All68 WAV files passed signal,
size and duration checks, then headless Chromium decoding and playback checks.
The browser checked normal-speed progress and accelerated completion with output
muted. This is not physical speaker acceptance or qualified phonetic approval.

The final exact-batch rehearsal restores181 main lessons and adds only136, for
**317 lessons/892 scored exercises/118 open tasks**. Earlier five writing bridges
and superseded roadmap drafts are excluded. The earlier322-lesson rehearsal is
historical and included those five bridges; it is not the proposed import scope.

Exact files, byte sizes, SHA-256 digests, lesson slugs, exercise keys and authored
prerequisites are pinned in
[the import manifest](manifest/IMPORT-MANIFEST-20261123.json). All136 lessons retain
their explicit [qualified-review flags](manifest/LESSON-REVIEW-20261123.json).
[Audio results](manifest/AUDIO-VALIDATION-20261123.json) contain generated-audio
metadata only. No new main import is authorized.

This is practice coverage, not complete educational coverage, an official exam
paper, independent qualified human approval or empirical CEFR calibration.
Three expressions are not a full 10–20-word vocabulary syllabus. Short synthetic
audio is not authentic varied-accent or spontaneous listening. Productive tasks
need qualitative human review. The roadmap's garbled lexical chart was not turned
into invented targets, and its assumption about the owner's level was not applied.
