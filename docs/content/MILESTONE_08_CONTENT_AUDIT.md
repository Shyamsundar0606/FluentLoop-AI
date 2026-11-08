# Milestone 08 content audit

The read-only audit examined the isolated M08 database at revision
`20261104_0009`. Canonical A1 source integrity matched the imported rows.
The review-packet validator found no structural issues in the three installed
A1 courses. The private output is `.publication-private/m08/m08_final_audit.json`.

| Release | Version | Lessons | Exercises | Status |
| --- | --- | ---: | ---: | --- |
| French from the Beginning | 1.0.2 | 10 | 50 | Draft |
| Être interactive fixture | 0.1.1 | 1 | 6 | Draft |
| A1 grammar and everyday French | 0.1.0 | 12 | 25 | Draft |

The canonical audit checks lesson and unit order, bilingual examples,
vocabulary associations, dialogue, answer keys, provenance and reference
paradigms against source. The M08.3 import validator checks topic, objective
and vocabulary links, listening scripts against bilingual examples, answer
variants and conjugation forms. The review packet also checks lesson level and
version, translations, repeated lexical identities, definitions, answer
configuration and Unicode. The first ten lessons retain their original keys
and their legacy exercise associations. Later items have explicit topic and
objective links.

| Finding for independent review | Action |
| --- | --- |
| A1 includes age inversion and a fixed polite conditional phrase | Confirm that teaching them as short expressions fits the intended scope |
| Stored pronunciation coverage is sparse | Review sound contrasts, Piper intelligibility and acceptable regional variation |
| Written grading distinguishes meaningful French accents | Confirm acceptable variants per exercise and test keyboard insertion |
| Listening practice repeats selected teaching examples | Decide which items should assess recall and which need unfamiliar examples |
| Source and attribution metadata are present, with rights review pending | Verify distribution terms and record licensing evidence |
| A2 through C2 have a curriculum blueprint | Author content only when ready for level-specific review |

See [the A1 grammar review](A1_GRAMMAR_CONTENT_REVIEW.md) and
[the exercise quality report](A1_EXERCISE_QUALITY_REPORT.md) for the earlier
inventory, correction history and format counts.
