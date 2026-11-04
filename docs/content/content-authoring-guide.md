# Content authoring guide

## Source format

The initial source is [`backend/content/a1/course.json`](../../backend/content/a1/course.json), encoded as UTF-8 JSON. It is parsed by strict Pydantic models in `backend/app/content_schemas.py`; unknown fields fail validation. Keep lessons in ascending stable slugs (`a1-001` through `a1-010`), and increment the `version` field when authored content changes.

Each beginner lesson includes an English introduction, 10–20 minute estimate, objectives, 8–15 vocabulary entries, French/English examples, grammar notes and examples, pronunciation guidance, a short dialogue, at least five exercises with explanations, and a recap. Add content that advances the learner from first sounds and words toward practical interactions; do not pad lessons with repetitive entries.

## Vocabulary conventions

- Store the bare French lemma, preserving accents and Unicode NFC spelling. Nouns use `grammatical_gender` (`masculine` or `feminine`) and do not include an article in the lemma. The current importer defensively strips a leading article from older source entries.
- Keep part of speech and gender in lexical identity. Never merge homographs solely because their spellings match.
- Provide an English translation and French definition for every sense. Add optional usage notes, irregularity notes, and IPA only when accurate.
- Use English `language_code` (`en`) for initial translations. Additional languages require reviewed translations and do not imply broader product support.
- Link examples in French and English. Preserve accents and punctuation exactly.

## Grammar and conjugation

Grammar topics have stable slugs; rules have stable codes within a topic. Explain conditions and common exceptions rather than giving misleading universal patterns. Include French/English example pairs.

The checked-in initial verb reference is restricted to present indicative forms for être, avoir, aller, faire, parler, habiter, and aimer. Do not generate full paradigms for other tenses without verification. IPA and audio references are optional; leave media associations null unless real reviewed media is available.

## Provenance, licensing, review, and publication

Every source must identify a name, type, license statement, and attribution requirements; include a source URL when applicable. Keep attribution and licensing claims factual. The checked-in A1 material is an AI-assisted draft, not independently human-authored or reviewed. Record the actual source and author contributions where known, and obtain an explicit rights/attribution decision before publication. Do not describe AI review as human review or copy protected third-party lessons.

Automated validation is not human review. Imports use `automated_checked` provenance while curriculum entities remain `draft`. Never claim `human_reviewed` or `published` without independent human review and recorded evidence. Publication requires an admin-prepared review JSON record covering language, pedagogy/sequence, answer keys for every lesson, and license/attribution. Each approval must include an independent reviewer, evidence reference, and timezone-aware review timestamp. The record is bound to the exact content version and source digest. License review must be signed off by someone other than the lesson reviewers.

```powershell
Push-Location backend
..\.venv312\Scripts\python.exe -m app.publish_content --review-record "<admin-approved-review-record.json>"
Pop-Location
```

The incomplete [A1 publication review template](./reviews/A1_PUBLICATION_REVIEW_TEMPLATE.json) is deliberately rejected by the command. Do not change pending fields to approved until the named humans have actually completed the relevant reviews and the evidence is recorded. Do not run publication automatically at startup or through a learner-facing API. There is no public content-edit or publish API.

## Safe content rendering

Sections are stored and rendered as text, not trusted HTML. Do not insert scripts, HTML fragments, externally hosted media, or arbitrary URLs into lesson bodies. Accessibility, accuracy, and publication review should be completed before the status change.
