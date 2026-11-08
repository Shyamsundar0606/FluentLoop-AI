# Milestone 09 AI coach architecture

The existing AI conversation remains the transcript for text and speaking.
M06 voice sessions link to that conversation, submit confirmed transcripts
through the same inference lease, and use the existing Piper and audio
retention paths. Coach options and completion use three additive fields
introduced by revision `20261108_0010`. Historic rows receive normal
difficulty, immediate feedback and a null completion date. The downgrade
refuses to discard saved coach data.

The tutor assembles a bounded prompt from the selected CEFR level, scoped
published progress, due cards, recent incorrect attempts and an aggregate
count of prior conversations with messages. It sends no previous conversation
transcript as personalization. Temporary difficulty adjusts wording within
the saved level. The original tutor message lease and request IDs protect
retries. Completion archives the conversation with a separate timestamp.

The existing AI API adds owned coach detail and option routes, finish, and
deletion for conversations without dependent speaking or study history.
Scenario replies use a structured Ollama response with optional correction.
The server validates the correction against the actual message and level.
The summary reads saved turns, corrections and literal scenario vocabulary
matches. Scenario goals remain separate from recorded activity. No mastery
score or second review scheduler is stored.

See [the design and existing service audit](MILESTONE_09_AI_LEARNING_DESIGN.md).
