# Exercise grading and content permissions

## Trust boundaries

The browser supplies only an answer and session IDs. It cannot choose answer
keys, scores, preview mode, activity keys, snapshots, learning objectives or TTS
scripts. New request models reject extra fields and permit exactly one answer
shape. Existing authentication, CSRF, password handling and user sessions are
unchanged.

The shared server grading service operates on a private validated snapshot.
Public session and curriculum projections whitelist display fields. Saved
structured answers are returned only in the owner's authenticated session after
submission. Answer keys are not passed to Ollama.

PostgreSQL transactions lock session/exercise rows and retain existing unique
attempt/idempotency constraints. Replays return prior grades; concurrent
submissions cannot advance progress twice. Completion is locked and idempotent.
Practice writes attempt/history data but never full lesson completion or SRS
updates. Migration downgrade guards prevent silent structured-data loss.

## Curriculum access

Parent lesson, unit and course must be published for ordinary accounts.
Developer preview requires both the existing backend flag and admin role, and
allows only draft/review/published parents. Archived/retired content is denied.
Grammar topics additionally have explicit publication state. Legacy `inherited`
topics use parent authorization; newly enriched implementation grammar is draft.

Checks apply to library, grammar, focused candidate selection, exercise APIs,
AI retrieval and session start. Session read, resume, answer, completion, results
and listening audio recheck live source/topic access. Session listings omit
revoked grammar sessions. Saved snapshots do not grant permanent access to
content whose permission has been revoked. Existing legacy snapshots retain
their original data structure.

Daily activities recheck their linked session sources. Objective recommendations
require recorded owned attempts, current source version and authorized source
exercises. Vocabulary review continues to use the existing backend publication
filters and unique enrolled review-card identities.

## AI and speech

Lesson actions pass a backend-authorized lesson UUID to existing conversation
services, not arbitrary browser text/context. The saved CEFR level must match.
They reuse existing AI and speech rate limits and CSRF dependencies. The existing
tutor retrieval is bounded and excludes exercise definitions, option answer
keys, attempts and private snapshots. Existing first-name minimization and
identity/history separation are retained; no email, password, token or age data
is added to model prompts.

Listening accepts no client TTS text and checks that the requested saved item
is a listening exercise owned by this session's learner. It reuses the existing
French worker, bounded output and speech request limit. Returned audio is
no-store and is not written to another audio database/cache. Existing speech
recording consent, retention, transcript editing/confirmation and deletion are
unchanged.

## Local verification boundary

M08 uses fresh `fluentloop_m08_*` databases and separate native loopback services.
Existing guarded M04–M07 browser/integration fixtures use their existing
`fluentloop_m05_*`, `fluentloop_m06_*` and `fluentloop_m07_*` prefixes. Synthetic
accounts and privileged browser expectations stay in ignored local directories.
No application learner rows are used for inference or test assertions.

Do not print `.env`, connection strings, private model tokens or learner rows.
The local helper reads existing private configuration, redacts subprocess
output and compares application data using aggregate table fingerprints only.
No main/preview service rebuild, database upgrade, reset or deployment is part
of M08 verification. No Git staging, commit, remote update or publication is
authorized by this milestone.
