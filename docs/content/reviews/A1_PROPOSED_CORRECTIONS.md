# A1 corrections proposed for independent review

> Historical 1.0.1 packet. The [1.0.2 correction results](A1_CONTENT_CORRECTION_RESULTS.md) and [current publication readiness](../../verification/A1_CURRICULUM_PUBLICATION_READINESS.md) supersede the deployed-state findings below. Independent approvals remain pending.

Prepared 3 November 2026. **Review proposals only: none of these changes has been applied to lesson source or a database.** No independent approval or license approval is claimed. The existing version 1.0.1 drafts and their publication states remain intact.

This accompanies [the lesson-by-lesson readiness report and reviewer checklist](A1_REVIEW_READINESS.md). Reviewers should approve or revise the wording below against the exact source version and evidence. The existing publication gate requires genuine, separate rights approval and lesson-level language, pedagogy and answer approvals. A proposal is not an approval.

## Concrete wording proposals

| Lesson and field | Proposed replacement | Answer-key impact |
|---|---|---|
| A1-001, exercise 5 prompt | `Which statement correctly compares French u /y/ with English oo /u/?` | Keep the existing three options and correct option index **1**. This aligns the prompt with its statement-shaped options. |
| A1-003, pronunciation | `In je m'appelle, the e in je is often reduced in natural speech, but beginners may pronounce it clearly. The double l in appelle is a spelling pattern: pronounce one /l/ sound, not two separate l sounds. Listen to an approved pronunciation model and repeat the whole phrase.` | None. Have a French phonetics reviewer verify the model before including it. |
| A1-004, pronunciation | `When counting or saying dix on its own, pronounce the final sound /s/: /dis/. Before a noun beginning with a consonant, as in dix livres, the final x is silent. Before a vowel sound, as in dix ans, a linking /z/ is heard. Learn these short expressions with their pronunciation models.` | None. This corrects the pause rule without treating every context as identical. |
| A1-005, exercise 1 prompt | `Which option means “a book”?` | Keep the existing options and correct option index **0** (`un livre`). |
| A1-005, exercise 1 explanation | `When it means a book, livre is masculine: un livre or le livre. Une livre is a different noun meaning a pound.` | None. The explanation now acknowledges the valid feminine noun rather than marking it universally incorrect. |
| A1-005, pronunciation | `Before a vowel sound, le and la shorten to l', as in l'ami and l'amie. The spelling l' does not show whether the noun is masculine or feminine. In un livre, un has a nasal vowel without a separate n sound. Before a vowel sound, as in un ami, a linking n is heard. In une, the n is pronounced.` | None. The reviewer should check regional nasal-vowel variation and the audio models. |
| A1-008, pronunciation | `In mon frère, do not add a separate n sound after mon. Before a vowel sound or silent h, a linking n is heard, as in mon ami. The s in les is silent in les livres; before a vowel sound, as in les amis, liaison produces /z/. Practice each expression as a unit.` | None. This qualifies the original blanket liaison statement. |
| A1-010, pronunciation | `In voudrais /vudʁɛ/, ou represents /u/ and the ending -ais represents /ɛ/. The word does not contain the spelling oi. Practice je voudrais as a polite expression meaning I would like. In l'eau and l'addition, the apostrophe shows that le or la is shortened before a vowel sound.` | None. A phonetics reviewer should approve the IPA and any recorded example. |

These are AI-assisted suggested edits, not independent linguistic findings signed off by a reviewer. The language references supporting the reported defects are linked in the readiness report. No dictionary entry or externally licensed recording is imported by this document.

## Pedagogy decisions still requiring a reviewer

- **A1-001:** Either supply rights-cleared, independently checked listening examples and actual sound-discrimination practice, or narrow the listening objective to match the existing written activities. A written multiple-choice answer alone does not demonstrate listening discrimination.
- **A1-003:** Explain the formal name question as a useful fixed expression before assessing it. Confirm pronunciation and natural register in the dialogue.
- **A1-004:** Explicitly teach `dix-huit` (18) and `vingt` (20) before the age examples, or choose examples within the already taught number range. The reviewer must decide how this fits the beginner sequence; no numbers or examples were changed here.
- **A1-006:** Gloss dialogue words such as `professeure` and `ici`, and explain `tu`/`vous` choices.
- **A1-007:** Scaffold negation and `pas de`; label the early `Je ne parle pas` example as a fixed expression or choose an already taught verb.
- **A1-008:** Teach `des` before requiring the plural-family dialogue.
- **A1-009:** Explain the connection between the earlier residence chunk and regular -er forms; gloss dialogue vocabulary and distinguish regular verbs from aller/faire.
- **A1-010:** Introduce the price/euro vocabulary used in activities. Teach `je voudrais` as a polite chunk without requiring a complete conditional paradigm.

## Technical correction proposals — no deployed repair performed

### A1-003: reconcile the main-only grammar link

The main database has both `introducing-yourself` and `basic-sentence-order`; the source and preview expect only the former. Have the curriculum owner decide whether the extra material should be retained in a revised source or detached from this lesson. Before applying that decision, inspect all links to the topic and preserve existing topic records, progress, exercise IDs and learning-session snapshots. Do not delete a shared grammar topic just to make the comparison green. Repeat the read-only audit in both stacks after an approved reconciliation.

### A1-009: explicit example-to-lexeme associations

The importer currently uses normalized substring matching of the stored lemma against the example text (`backend/app/content_import.py`). Inflected forms can therefore miss their infinitive: `habite` does not contain `habiter`, and `parlons` does not contain `parler`.

Proposed associations for review:

| Existing sentence | Existing lesson lexeme | Translation to retain |
|---|---|---|
| `J'habite à Lyon.` | `habiter` | `I live in Lyon.` |
| `Nous parlons français.` | `parler` | `We speak French.` |

A future approved importer correction should use reviewed, explicit associations or a narrowly validated conjugation-aware mapping. Avoid assigning every orphaned example to an arbitrary first word. Preserve existing sentence and lexeme IDs; add missing relationships idempotently with truthful provenance. Regression coverage should check these two links, reject unrelated-verb links, run import twice without duplicates, and preserve learning/session data. Then repeat the deployed audit. This proposal does not modify the importer or backfill either database.

## Review and application sequence

1. Review these proposals with the original source, authorized preview and readiness report. Record genuine reviewer decisions and rights evidence; unresolved items stay pending.
2. Apply only the approved corrections in a separately tracked content revision, updating the version/digest and source metadata accurately. Preserve the prior draft and existing user records.
3. Validate source, importer behavior, both deployed comparisons, answer keys and learner/preview permissions against the revised material.
4. Obtain complete genuine approvals bound to the final version and canonical digest through the existing review-record workflow. Rights approval requires a separate reviewer from the lesson reviewers.
5. Publish only through the existing authorized publication workflow after its conditions are met. No publication command was run for this proposal.
