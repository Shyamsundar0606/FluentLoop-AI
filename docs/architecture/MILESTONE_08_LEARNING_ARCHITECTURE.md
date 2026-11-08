# Milestone 08 learning architecture

The curriculum importer provides lesson, grammar, vocabulary and exercise
records. The existing authorization layer filters content before the learning
service creates a session. The server freezes the lesson context and answer
definitions, then returns a projection without answer keys. Submissions are
owned and graded inside the existing transaction. Idempotency keys protect
retries. Results and recommendations consume persisted attempts.

Full lessons and focused practice use the same session engine and separate
activity keys. A retry launched from a mistake card resolves the owned,
current attempt to its source exercise. Grammar shows the latest recorded
result per linked exercise in the bounded recent window. Topic practice does
not increment full lesson completion. The existing daily plan and spaced
repetition services keep their own completion and scheduling rules.

The lesson library batches the unit, objective, active-session and progress
queries for the set of permitted lessons. Grammar batches exercise
availability and recent attempt summaries rather than querying availability
separately for every topic. Listening uses the existing bounded Piper service
and delivers audio through authorized exercise or reviewer routes.

Curriculum review is separate from preview and from learning history. The
review service derives a digest of the current course packet and appends
decisions to the versioned course provenance under a transaction lock.
Qualification grants come from server configuration. The publication command
checks the current decisions alongside the earlier canonical source integrity
checks and verified administrator authorization. No new schema revision is
needed. The existing `20261104_0009` migration remains the learning schema
head. See [the engine design](interactive-learning-engine.md) for snapshot
and grading details.
