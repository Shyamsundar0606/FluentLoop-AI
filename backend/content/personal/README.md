# Personal curriculum review release 0.2.1

## Authorized personal import — 22 November 2026

The owner subsequently authorized the six existing packs for personal use. All
72 lessons and 324 exercises were imported into main `fluentloop` as unpublished
drafts after a fresh verified backup. The atomic import verified that every
pre-existing row was unchanged and no existing record was deleted. Total lessons
are now 82: 22 at A1 and 12 each at A2, B1, B2, C1 and C2. Repeat-import reuse and
source digests were checked; the separate M08 database remains unchanged.

This does not make the curriculum exhaustive or human-approved. The additional
A0/A1 foundation releases are a different batch and remain staged, requiring
separate authorization. Historical review statements below describe the state
before this explicitly authorized import.

These original AI-assisted manuscripts are **unpublished drafts**. They have been
authored for disposable-database validation and owner review. Do not import into
the main `fluentloop` database without separate authorization. Do not merge M08.

| Target level | Modules | Lessons | Objective exercises | Open writing tasks | New grammar topics | Lexical expressions |
|---|---:|---:|---:|---:|---:|---:|
| A1 | 3 | 12 | 54 | 3 | 3 | 9 |
| A2 | 3 | 12 | 54 | 3 | 3 | 9 |
| B1 | 3 | 12 | 54 | 3 | 3 | 9 |
| B2 | 3 | 12 | 54 | 3 | 3 | 9 |
| C1 | 3 | 12 | 54 | 3 | 3 | 9 |
| C2 | 3 | 12 | 54 | 3 | 3 | 9 |
| Total | 18 | 72 | 324 | 18 | 18 | 54 |

Each module includes grammar, vocabulary, reading and writing lessons. The first
three use all six existing objective formats; writing preserves an open response
with advisory feedback. Speaking extensions reuse the app's Tutor/voice workflows.
Exact-model recall and reconstruction are explicitly labelled: alternative valid
French translations or word orders are not assessed by those narrow drills.

Situations progress from errands, directions and appointments to housing, travel,
interviews, formal requests, argument, qualification and context-sensitive register.
All passages and definitions were authored for this project. They are fictional
practice, not legal, medical or administrative guidance. CEFR labels are intended
practice targets, not independent placement judgements or an exhaustive syllabus.

All five independent review categories remain pending: linguistic accuracy,
phonetics, pedagogy, answer keys and licensing. Automated grading and schema
validation do not replace these reviews. In particular, review level suitability,
the repeated model drills, distractor quality and natural spoken delivery before
using this material beyond personal draft practice. No pronunciation certification
is provided by speech recognition.

## Second-pass review, 22 November 2026

**72/72 lessons and 324/324 exercises pass the revised source/schema and grading
checks. 0/72 have independent human approval.** This was a separate, reference-
checked AI review of all 18 situation groups and their four lesson variants,
not an independent human or accredited CEFR evaluation. No approval records were
created and no curriculum was imported into main `fluentloop` or M08.

The revised files are `*-personal-0.2.1.json`. Earlier 0.2.0 manuscripts and the
builder are preserved in the ignored private review evidence. The older release
in the disposable database remains unchanged; 0.2.1 has distinct immutable keys.

Corrections made:

- A1 supermarket question now asks what the customer is looking for; the passage
  did not establish what was bought. The bus-stop position is now explicit.
- A2 `charges comprises` now means service charges included, with a definition
  that does not imply every household bill is included. The ticket-office passage
  now connects its opening sentences naturally.
- Each gap identifies the requested verb/tense or fixed construction, preventing
  a valid alternative such as `veux` or `peux` being rejected by an unspecified
  one-key task. Exact-model recall/reconstruction remains clearly labelled.
- Listening distractors now differ in a relevant detail, tense, agent or logical
  relation. Choice keys occupy each of the three positions 36 times across the
  108 choice/listening items, rather than always appearing first.
- Feedback now explains the relevant passage, lexical pairs or audio meaning,
  instead of returning the grammar explanation for every exercise format.
- All 18 writing prompts now specify the situation and communicative task.
  Argument, synthesis and audience/register work replace generic request-and-
  closing instructions at advanced levels. Each skill has an explicit lesson focus.

Validation rerun: 20 affected curriculum/assessment tests passed, with two existing
dependency deprecation warnings. All 324 keys accepted their authored answers and
rejected deliberately incorrect answers. Tests also check matching meanings,
audio/translation links, NFC, balanced answer positions, source/builder consistency,
idempotency, older digest compatibility, snapshot persistence and ordinary denial.
A PostgreSQL check imported **only into the existing disposable curriculum DB**:
72 revised lessons, 324 exercises; all draft, source digests consistent, repeat
imports reused, older disposable lesson/exercise hashes unchanged.

CEFR labels remain **provisional practice targets**. The review considered basic
requests at A1, familiar everyday exchanges at A2, connected narration/explanation
at B1, supported argument at B2, structured nuanced analysis at C1, and precise
register/implicit meaning at C2. These are local task-design judgements informed
by the [Council of Europe descriptors](https://www.coe.int/en/web/common-european-framework-reference-languages/cefr-descriptors-search),
not a grammar-item-to-level certification. Word-count ranges are local scaffolds,
not official CEFR requirements.

Remaining issues before independent sign-off: validate CEFR difficulty with a
qualified FLE reviewer/learners, especially the short C1/C2 readings and scaffolded
objective drills; review spoken delivery with a listener; and complete the five
independent review categories. Four lessons per situation intentionally reuse a
passage/model. The 72 lessons represent 18 situations, not 72 distinct long texts.
Open writing and speaking require qualitative review; deterministic drill success
does not demonstrate free production or broad proficiency.

The existing immutable assessment importer adds versioned courses and references
without replacing older lessons, frozen snapshots, answer keys or shared meanings.
New glossary entries cannot rewrite an existing lexical meaning. A changed release
requires a new version. The builder only writes manuscripts; it never imports them.

Rebuild/validate source from the project root:

```powershell
$env:DATABASE_URL='sqlite://'
.\.venv312\Scripts\python.exe backend\scripts\build_personal_curriculum.py
```

Reference checks for the advanced concession patterns (not source passages and
not independent review approvals): [OQLF, quelque / quel que](https://vitrinelinguistique.oqlf.gouv.qc.ca/21570/la-grammaire/les-homophones-grammaticaux/les-homophones-quelque-et-quel-que),
[Académie française, si](https://www.dictionnaire-academie.fr/article/A8S0896).
