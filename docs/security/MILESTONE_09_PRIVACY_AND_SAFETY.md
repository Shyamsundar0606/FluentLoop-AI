# Milestone 09 privacy and safety

Coach detail, settings and completion require ownership. Mutations use the
existing session, origin, CSRF and rate limit checks. Learners may delete
standalone tutor conversations. Conversations linked to speaking or study
history are protected by existing foreign keys, and audio deletion remains
available through the existing speech controls.

Coach personalization selects completed lessons, grammar topics, review
cards and mistakes within the user's published content scope. It sends
aggregate counts and bounded vocabulary rather than answer keys, old learner
sentences or profile details. Scenario prompts omit profile names. Ordinary
retrieval skips globally shared lexical examples and requires published
provenance for grammar rules. Source visibility and version checks still
apply after inference and when historical transcripts are read.

The existing prompt separates untrusted data from instructions. The tutor
has no tools or permission to update curriculum, CEFR or scheduling. Its
French corrections are suggestions. The application labels general model
knowledge separately from curriculum context. The doctor and pharmacy
scenarios use authored text, so they do not ask the model to interpret real
health information.

Speech retains the M06 boundaries. Raw recordings are opt-in for retention.
Transcripts and recognized words are neither acoustic assessment nor a
certified pronunciation result.
