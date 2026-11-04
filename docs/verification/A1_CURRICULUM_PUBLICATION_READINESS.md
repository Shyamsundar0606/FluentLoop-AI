# A1 curriculum publication readiness

Date: 2026-11-04. Branch: `feature/a1-curriculum-review`, based on published main `1ce7dcca690b7720dbd4ea0d846b6babf2130c31`.

**Technical correction/validation complete; independent review and publication approval are still pending. All ten lessons remain draft in both application databases. No application publication command was run. No Milestone 08, new navigation, paid dependency or database migration was introduced.**

## Exact revision and lesson status

Current authored source: `backend/content/a1/course.json`, **1.0.2**. Previous 1.0.1 draft is archived unchanged. Every existing slug/title is retained; see the [ten-lesson correction table](../content/reviews/A1_CONTENT_CORRECTION_RESULTS.md).

- Canonical source SHA-256: `f8ce674247b030ba06efc32f5a58063a943f4b0926ced8133b932edcb0dcb8ad`.
- Importer SHA-256: `c2ea75470be01b0a7beae82a90a8f56919d3ea8c1365a0f40c551b1ded5477ff`.
- Source: 10 lessons, 83 vocabulary occurrences / 77 normalized lexical identities, 20 explicit example packets, 50 exercises / 150 unchanged options and 50 unchanged correct indices.
- Main and preview: **10/10 lesson integrity comparisons pass, 10 draft lessons, 0 published**. Metadata, source/import digest, translations, explicit associations, grammar, dialogue order, keys and seven existing present-tense paradigms pass technical checks.
- All six CEFR levels remain A1, A2, B1, B2, C1 and C2. No duplicate lessons or new higher-level lesson content was created.

The digests bind the current packet; they do not prove linguistic correctness or rights. If content, source metadata or reference implementation changes, refresh the packet and repeat applicable reviews.

## Measured database import results

Counts below are actual importer operation counters, not guessed distinct-row totals.

| Stack / operation | Inserted | Updated | Deleted | Unchanged | Rejected |
| --- | ---: | ---: | ---: | ---: | ---: |
| Main: 1.0.1 to 1.0.2 | 935 | 52 | 6 | 970 | 0 |
| Preview: 1.0.1 to 1.0.2 | 935 | 52 | 5 | 970 | 0 |
| Main: repeated 1.0.2 import | 0 | 0 | 0 | 1956 | 0 |
| Preview: repeated 1.0.2 import | 0 | 0 | 0 | 1956 | 0 |

The 935 inserted rows in each stack comprise **one import batch, 923 versioned automated provenance rows, one replacement grammar example and ten explicit example associations**. No new lesson, exercise, option, lexical or sense IDs were created in the deployed upgrade.

The deleted rows are curriculum-only: one obsolete grammar example plus four stale lexical-example associations in each stack; main additionally detaches its extra lesson-to-grammar membership. Shared grammar topics and all lexical/sense records remain. Existing historical lexical aliases are retained rather than merged at the expense of card references. Fresh imports normalize to 77 identities; upgrades can retain an extra alias ID.

Source validation and CLI dry-run passed in the built backend. The final read-only audit matches 1.0.2 in both deployed databases. No draft was human-approved or published by import.

## History and database preservation

Before updates, private read-only snapshots recorded all **59 public tables** in each stack, account counts, lesson IDs/versions and Alembic head. Isolated SQLite and real PostgreSQL tests first reproduced legacy malformed nouns and an obsolete grammar link, then exercised re-import twice while preserving IDs, active lesson snapshots, an existing graded attempt/score, a daily plan, review cards/attempts, AI messages and uncertain speech history. A resumed session still returns its original 1.0.1 prompt/version and score after source correction.

During each application import transaction, **all 28 non-curriculum/protected table fingerprints remained identical**. Existing course, unit, lesson, exercise, option, lexeme and sense ID sets were explicitly checked and retained. No database, volume or learner record was reset or deleted. Alembic remains **20261104_0008 (head)** in both stacks, with no added migration.

After backend restarts, preview still has 28/28 matching protected hashes. Main has 27/28 matching hashes with **all 28 row counts unchanged**: its existing minute-based audio-retention cleanup soft-deleted one already expired audio asset. The asset row remains; expiry was at or before its deletion timestamp. Account/auth/profile/progress, learning/review, AI, speech-turn/session and pronunciation-history hashes remain unchanged. This routine retention exception is distinct from import changes; no expired audio was restored or privacy retention disabled.

Only the two backends were rebuilt/recreated. Existing database, Redis, email, frontend and speech-worker services/volumes were retained. Both Compose configurations validate; both APIs are ready and all twelve application services are healthy.

## Controlled publication workflow

The existing local publisher is reused. The version-2 approval record now requires:

1. Current content version and canonical source **and importer** digests.
2. Identified reviewers, relevant qualifications, independence attestations, evidence and timezone-aware dates for French, pedagogy, answer keys and dependencies of every lesson.
3. The explicit predecessor dependency chain; all ten prerequisite reviews must be complete.
4. Separate licensing/attribution approval, from a reviewer separate from every lesson reviewer.
5. An explicit current-administrator publication decision with evidence, after all reviews; future-dated records fail.
6. A fresh read-only audit of actual imported content before any publication status is changed. Source/database drift blocks publication even when an earlier import succeeded.

The course/admin rows are locked during publication checks. Schema-1 records cannot bypass the strengthened gate. The [structured version-2 template](../content/reviews/A1_PUBLICATION_REVIEW_TEMPLATE.json) remains pending, with null identities/dates, blank qualifications/evidence and false independence flags; it deliberately fails validation. Synthetic positive/negative approvals exist only in isolated tests.

The gate verifies structured attestations and current database state. It cannot prove qualifications, signature authenticity or legal ownership from JSON. A trusted authorized operator must verify genuine evidence. This command remains a local administrative tool, not a public API or startup task.

## Executed tests

| Check | Result |
| --- | --- |
| Complete native backend pytest, including opt-in PostgreSQL | **223 passed, zero skips**, two existing dependency deprecation warnings. |
| Focused final correction/audit/publication suite | **31 passed**, including legacy repair on actual isolated PostgreSQL and unrelated-verb rejection. |
| Frontend ESLint / TypeScript | Passed; type generation runs before TypeScript. Reran after adding the focused A1 browser test. |
| Production build | Passed, **35 pages**. No frontend features, design or navigation changes. |
| Existing account/text/learning browser group | **11 passed** against controlled mocks and the isolated real API as appropriate. |
| Responsive/voice browser regression | **9 unique cases passed** across quota-respecting isolated groups, including microphone lifecycle, editable uncertain transcripts, explicit confirmation, original/history retention and access isolation. |
| M07 daily-learning/review browser group | **3 passed** against actual isolated PostgreSQL, including level/history persistence and ordinary-learner draft denial. |
| Existing live lesson grading / resume / owner denial | **1 passed**. |
| New corrected A1 browser regression | **1 passed**: all ten authorized lesson pages, corrected dix/voudrais wording, draft labeling, withheld answer keys and revised book exercise with 1.0.2 session version. |
| Total browser coverage | **25 unique scenarios passed across isolated runs**. This is not one unconfigured all-tests run or a physical-device microphone claim. |
| Docker / PostgreSQL | Both backend images built, both Compose configurations passed, both existing migration heads verified, both APIs ready; twelve services healthy. |

Browser/model fakes remain explicitly guarded test-only dependencies. Speech-policy, decoding and voice-style regressions remain in the native suite; no ASR threshold or acoustic scoring feature changed. All test accounts and raw reports/recordings are isolated and excluded from publication.

## Remaining blockers and next approval steps

- Obtain genuine qualified French/phonetics review of every packet, including IPA/liaison/regional variation and each remaining question in the correction report.
- Obtain pedagogical/prerequisite and all 50 answer-key approvals against the final exact version.
- Establish ownership, permissions and attribution for lesson text/reference material and any future audio. Source metadata still truthfully asserts no publication license and pending rights review. A dictionary citation is not redistribution permission.
- Resolve the scope of alphabet/listening coverage and the retained legacy alias records with the curriculum owner; ten lessons are not a complete accredited A1 course.
- Update metadata/version/digests if reviewers request changes; do not carry old approvals onto edited material.
- Complete genuine records using [the independent checklist](../content/reviews/A1_INDEPENDENT_REVIEW_CHECKLIST.md), review the feature PR and obtain an explicit authorized publication decision. **Do not merge or publish automatically.**

Acoustic pronunciation scoring remains unvalidated/unavailable. White-and-purple UI, the five existing destinations, authentication, personalization and M01–07 functionality are retained. Raw local audits, account details, database before-images, recordings and generated audio stay private.

Final packaging verification: the shared auditor locates source/reference files relative to the installed package, not a repository-only directory layout. Its CLI passed inside both final Docker backend containers in read-only transactions (10 drafts, technical integrity true, publication approval false). The final focused 31-case suite includes strict English-translation drift rejection and real PostgreSQL preservation.
