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

The importer runs in one database transaction. Stable slugs, lexical identity, sequence, and natural keys make it safe to rerun: unchanged rows are left as-is, changed authored values are updated, and new rows are inserted. For each source-managed grammar rule, it also removes obsolete grammar-example rows that are no longer in the current source; examples still present anywhere in the current source for that rule are retained. The batch report includes this scoped `deleted` count. No other rows are implicitly deleted or unrelated records overwritten. A failed operation rolls back.

Imports create/update draft content and automated-check provenance only. They do not publish. Each version records a source digest: changing JSON without incrementing its content version is rejected. When a new version changes a published record, that record returns to draft and must be reviewed again. An unchanged re-import preserves publication status and review evidence.

## Publication

Publication is a separate trusted local operation. It verifies the complete ten-lesson A1 structure, level values, at least five exercises per lesson, one correct option per multiple-choice exercise, and validated provenance. Run it only after independent human review and license review:

```powershell
Push-Location backend
..\.venv312\Scripts\python.exe -m app.publish_content --review-record "<admin-approved-review-record.json>"
Pop-Location
```

The review record must be complete, independently signed off, and match the exact imported content version and source digest. It must include French-language, pedagogy/sequence, and answer-key approval for every lesson plus a separate licensing/attribution approval. `docs/content/reviews/A1_PUBLICATION_REVIEW_TEMPLATE.json` is intentionally incomplete and will fail validation. Do not expose this command through FastAPI or run it automatically during application startup.

## Recovery

Database changes roll back on import failure. Correct the source JSON, rerun `--validate-only`, inspect the dry-run, then apply again. The only import-time deletion is the source-scoped grammar-example reconciliation described above. Retiring other authored records requires a separately reviewed administrative change rather than ad hoc bulk deletion. Do not drop the application database, user tables, or PostgreSQL volume for content recovery.
