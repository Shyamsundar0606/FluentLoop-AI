# Exercise formats and deterministic grading

Every answer includes the owned `session_exercise_id` and a UUID
`idempotency_key`. Submit exactly one of the following payload shapes to the
existing session answer route.

| Format | Answer field | Server authority |
| --- | --- | --- |
| Multiple choice | `selected_option_id` UUID | Must belong to the saved exercise; one authored correct option |
| Fill blank | `text_answer` (1–1000 characters) | Exact membership after bounded normalization |
| Sentence order | `tile_ids` (1–30 UUIDs) | Every saved tile exactly once; explicit accepted orders only |
| Matching | `matches` (up to 12 UUID → UUID entries) | Complete one-to-one mapping of saved left/right IDs |
| Listening | `selected_option_id` UUID | Same saved choice grading; the audio script remains private |
| Short written response | `text_answer` | Explicit authored variants only; no fuzzy/LLM assessment |

The existing `translation` type remains a deterministic written-response alias.
Unsupported or subjective definitions fail safely instead of receiving an
invented authoritative grade.

Written normalization uses Unicode NFC, case folding, curly/straight apostrophe
equivalence, reasonable whitespace and trailing sentence punctuation. Accents
remain significant: `étudiant` and `etudiant` are different. It does not correct
spelling or silently replace a learner's sentence.

Tiles and matching sides are shuffled independently once per saved session.
Public responses contain only display text and opaque IDs. They exclude
`accepted_orders`, `answer_pairs`, `accepted_answers`, `correct_option_id`,
`correct_sentence`, `exercise_data` and the listening script. Option ordering
does not mark which choice is correct. Authoritative feedback is disclosed only
after a valid submitted attempt for that exercise.

For listening, request audio using the session/exercise audio endpoint. It
rechecks ownership and live publication permissions, accepts no client-supplied
text, uses existing Piper through the existing worker and returns bounded WAV
bytes with `Cache-Control: no-store`. It reuses the existing speech rate limit.
If audio is unavailable, show a retry message; the attempt remains unanswered.
Native controls support play, pause and replay. Listening is comprehension,
not acoustic pronunciation assessment.

The UI retains unfinished answers during recoverable save failures and retries
the same payload/key. Saved attempts and their raw submitted payloads are
available only to their authenticated owner. After leaving and resuming, prior
server feedback and completed answers remain visible. Unsubmitted input is
component state, not a cross-device draft; submit before leaving to persist it.

## Example request

```json
{
  "session_exercise_id": "00000000-0000-4000-8000-000000000001",
  "idempotency_key": "00000000-0000-4000-8000-000000000002",
  "text_answer": "Je suis étudiante."
}
```

Malformed IDs, extra answer fields, a wrong payload type, missing tiles,
duplicate tiles, incomplete matches and foreign options produce validation
errors. A wrong but well-formed answer is recorded once with supportive saved
feedback. An existing answered exercise cannot be changed by reusing another
idempotency key.
