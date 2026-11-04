# Vocabulary scheduling

Algorithm version: **`fl-sm2-v1`**. This is a small deterministic SM-2-inspired policy, not the original SM-2 and not a clinically or empirically calibrated retention model. The original [SuperMemo SM-2 description](https://super-memory.org/archive/english/ol/sm2.htm) is background for increasing intervals and ease; FluentLoop's initial intervals, rating interpretation and lapse rule are explicitly different. No source code from that implementation was copied.

## Cards and grading

Enroll only existing word senses reached through currently authorized lesson vocabulary. New cards follow curriculum order. A card identity is user + word sense + CEFR level + card type. The first supported card asks for a French word/expression from its stored English meaning (`english_to_french`). Cards have stable UUIDs and a digest of the actual prompt, authorized answer set and explanation.

Each session contains at most 20 cards; the focused UI and daily plan assign three. Enrollment happens on an explicit session start, not merely by opening Home or reading a due count. Due cards precede unseen cards. An active session at the selected level is resumed rather than silently replaced.

French equivalents are accepted only when existing, currently permitted records have the exact same English prompt. No synonyms or vocabulary rows are invented. Meaning-only prompts do not test a particular grammatical gender; this limitation is explicit. Context-sensitive exercises need reviewed associations in a future revision.

Grading normalizes Unicode NFC, letter case, whitespace, straight/curly apostrophes, supported dash forms and terminal punctuation. Accents are preserved: `ecole` is not accepted for `école`; composed and decomposed `é` are equivalent. There is no edit-distance or model-based spelling forgiveness. HTTP input is bounded to 300 characters, nonblank, with invalid controls and extra authoritative fields rejected.

Question APIs return the English prompt and typed-answer instruction. Correct French answers and explanations appear only after an authenticated valid submission. Private session-item snapshots retain the exact answer set used for grading. If current content or permitted alternatives change, block stale grading and hide stale content; allow closing the unavailable session, then starting a new one. Preserve its history.

## States and intervals

| Event | State | Repetitions | Next review |
|---|---|---:|---|
| Newly enrolled, unseen | new | 0 | Now, in the created session |
| First correct answer | learning | 1 | 1 day later |
| Second consecutive correct answer | review | 2 | 3 days later |
| Later correct answer | review | +1 | Round(previous interval × adjusted ease), bounded 1–365 days |
| Incorrect answer | relearning | 0 | 10 minutes later |

Start ease at 2.5. A correct answer rated easy adds 0.15; difficult subtracts 0.15; normal/absent leaves it unchanged. Clamp ease to 1.3–3.0. An incorrect answer subtracts 0.2, increments lapses and uses the ten-minute interval regardless of rating. Correctness comes only from server grading; confidence never overrides it. Later interval rounding uses Python's `round` in this version. A lapse interval is stored as `10/1440` days plus the exact UTC due timestamp.

A session presents each assigned card once. A failed card does not loop immediately in that session. Merely viewing a card never changes its schedule. Store UTC aware due/review timestamps; a one-day interval means elapsed 24 hours, not a local-midnight boundary.

Example from `2026-11-04T12:00:00Z`: a new correct card is due November 5 at 12:00 UTC. Its next correct review is due three days after that review. An incorrect answer at the initial time is due November 4 at 12:10 UTC, even if the learner selected easy.

## Transactions and history

Lock the owned review session and card for grading. A unique session/request UUID and unique session item prevent repeated answers from scheduling twice. Identical retries return the stored result; changed payloads or another request for an answered item return conflict. Commit the immutable attempt and card schedule in one transaction. Save previous/new due time and interval, before/after scheduling parameters, correctness, rating, algorithm version and actual review time.

History is metadata-only after permissions change. No review rows are erased when levels change or preview access is revoked. Progress counts actual attempts and distinct studied word senses, with due counts at the current saved level. There are no fabricated time-on-task or retention percentages.

Limitations: fixed heuristic intervals, no learner-calibrated retention prediction, no acoustic pronunciation scoring, typed translation only, no unreviewed auto-generated vocabulary, and no claim that draft-preview source records are expert-correct. Source quality remains governed by the independent curriculum review workflow.
