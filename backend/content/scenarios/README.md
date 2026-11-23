> Current checkpoint —23 November2026: this exact batch is now imported into the personal main database as unpublished drafts after direct owner authorization, fresh verified backup and disposable restore rehearsal. The older staging statements below describe the pre-import review. Qualified human review and empirical calibration remain pending. No future batch is authorized.

# Scenario draft release — 22 November 2026

Seven original AI-assisted two-lesson modules: one receptive scenario with four
scored exercises, followed by an open writing/speaking transfer and revision task.
Total: **14 lessons, 28 scored exercises, seven open transfer tasks**. The scored
items test contextual detail, inference, listening and lexical meaning. They do
not represent a comprehensive four-skill assessment battery.

These files are staged only. No release 0.4.x is authorized for the main database.
The manifest records source hashes and disposable PostgreSQL validation. Existing
0.2.1/0.3.x releases must remain immutable.

| Stage | Situation | Main demand |
|---|---|---|
| A0 | Bakery | Supported recognition and polite memorised chunks |
| A1 | Market | Quantity, colour, total price and simple clarification |
| A2 | Delayed journey | Event sequence and an updated meeting arrangement |
| B1 | Housing repair | Distinguish a request, an assumption and a commitment |
| B2 | University access | Evaluate limited statistics and a conditional proposal |
| C1 | Workplace pilot | Mediate conflicting evidence and methodological limits |
| C2 | Administrative access | Interpret irony, presupposition and register |

The learning map provides recommended preparation; the transfer task also has an
explicit prerequisite on its scenario lesson. At A0/A1 the models are intentionally
supported. At B2–C2 the input is still a short pedagogical excerpt: extended,
multi-source and authentic multi-speaker material remains a coverage gap. Scripted
synthetic listening is not evidence of understanding all native speech. Open tasks
provide self-review criteria and existing advisory AI feedback, not calibrated
CEFR scores. Spaced retrieval instructions supplement the existing saved-error
and vocabulary workflows; they do not add a new scheduling engine.

## Reference-based editorial review

The [Council of Europe Companion Volume](https://www.coe.int/en/web/common-european-framework-reference-languages/cefr-companion-volume-and-its-language-versions)
was consulted for progression in inference, mediation and audience-sensitive
expression. The activities are original, not copied passages or official exam
items. The mapping is a design interpretation, not independent calibration.
French wording, translations, answer-key scope and sequencing received AI-assisted
editorial checks. Distractors contradict the supplied context or overstate it;
correct answers deliberately preserve qualifications. All correct and deliberately
wrong answers were checked mechanically. Qualified independent human language,
phonetic, pedagogical and CEFR review remains **pending** for every release.

An initial A0 0.4.0 rehearsal exposed a conflict with the canonical shared meaning
of `merci` in the complete original-course regression fixture. The guard rejected
the import. Corrected A0 0.4.7 reuses that definition; the earlier source is retained
under `archive/`, excluded from active pack imports. The current batch was then
rehearsed against the fresh disposable main restore containing all 101 lessons.
Never import the archived release. No protected database was changed by this fix.

Reproduce with `backend/scripts/build_scenario_curriculum.py`; validate in a
disposable database through the existing assessment importer. Never use a source
generation command as authorization to import into the protected main database.
