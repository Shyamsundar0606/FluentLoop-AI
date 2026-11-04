# Content import guide

## Requirements

Apply database migration `20261101_0003` before importing curriculum data. Import uses the configured backend database URL; verify it points to the intended development or isolated test database before using `--apply`.

## Validate and preview

Run from the repository root in PowerShell:

```powershell
Push-Location backend
..\.venv312\Scripts\python.exe -m app.content_import --validate-only
..\.venv312\Scripts\python.exe -m app.content_import --dry-run
Pop-Location
```

Both operations validate the JSON source with strict Pydantic schemas and do not write to PostgreSQL. Validation diagnostics include the source file and field path. Checks include required fields, six-level identifiers, stable lesson IDs/positions, duplicate lexical identities, Unicode normalization, translations, dialogue turns, exercise option/answer identity, exercise minimums, and planned A2–C2 coverage.

## Apply and repeat

```powershell
Push-Location backend
..\.venv312\Scripts\python.exe -m app.content_import --apply
..\.venv312\Scripts\python.exe -m app.content_report
Pop-Location
```

The importer runs in one database transaction. Stable slugs, lexical identity, sequence and natural keys preserve existing records. Known noun article-stripping defects are repaired in their existing vocabulary slots so lexical/sense/card references remain valid. Explicit example references replace substring guesses. Shared notes are resolved consistently before import.

Scoped deletions reconcile obsolete source-managed grammar examples, lesson-to-grammar memberships and example-to-lexeme associations within the authored lesson. Shared grammar topics and lexical records are retained. No learner history is deleted or rewritten; saved learning/review snapshots keep their original content version. The report includes actual inserted, updated, deleted, unchanged and rejected operation counts. A failed operation rolls back. Version 1.0.1 remains archived; current revisions require explicit example vocabulary references.

Imports create/update draft content and automated-check provenance only. They do not publish. Each version records a source digest: changing JSON without incrementing its content version is rejected. When a new version changes a published record, that record returns to draft and must be reviewed again. An unchanged re-import preserves publication status and review evidence.

## Publication

Publication is a separate trusted local operation. It verifies the complete ten-lesson A1 structure, level values, at least five exercises per lesson, one correct option per multiple-choice exercise, and validated provenance. Run it only after independent human review and license review:

```powershell
Push-Location backend
..\.venv312\Scripts\python.exe -m app.publish_content --review-record "<admin-approved-review-record.json>"
Pop-Location
```

The version-2 review record must match the imported version, canonical source digest and exact importer digest. It requires identified, qualified independent reviewers with evidence and timezone-aware dates for language, pedagogy, answers and the preceding-lesson dependency of every packet. Rights approval requires a separate reviewer. A current administrator must record an explicit publication decision after all reviews. The publisher repeats the read-only source/database audit and blocks drift or future-dated approvals before changing statuses.

`docs/content/reviews/A1_PUBLICATION_REVIEW_TEMPLATE.json` remains intentionally pending and fails validation. Schema-1 records do not satisfy the strengthened gate. See [the independent checklist](reviews/A1_INDEPENDENT_REVIEW_CHECKLIST.md). The trusted local operator must verify genuine qualifications, signatures and rights evidence; software cannot establish those facts from JSON alone. Do not expose this command through FastAPI or run it automatically at startup.

## Recovery

Database changes roll back on import failure. Correct the source JSON, rerun `--validate-only`, inspect the dry-run, then apply again. Import-time deletions are limited to the source-scoped associations/examples described above. Retiring other authored records requires a separately reviewed administrative change. Do not drop the application database, user tables or PostgreSQL volume for content recovery.
