# Milestone 09 local verification

The implementation is on the local `feature/milestone-09-ai-learning-coach`
branch. Alembic revision `20261108_0010` adds coach options and completion
metadata to existing tables. Migration and browser verification use
disposable databases. The existing main and preview databases are outside
the write scope.

## Reproduce verification

Run from the project root in PowerShell with local PostgreSQL, Redis,
Ollama and the speech worker available:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py tests
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py --coach
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py
Push-Location frontend
npm run lint
npm run typecheck
Pop-Location
```

The coach and previous learning browser suites use separate disposable
instances so each fits within the existing login rate limit. The production
build is part of the runner. The microphone test uses an ignored synthetic
French audio fixture as its browser input and sends the browser-recorded
audio through the real Faster-Whisper, Ollama and Piper path. No paid AI
service is needed.

The complete backend run passed **264 tests** with two dependency
deprecation warnings. The final focused run passed **38 tests**, including
the additional regression for a draft example linked to published
vocabulary. ESLint, TypeScript, the production build, and the redacted secret
scan passed. Redis returned `PONG`. A read-only check found the existing
M08 demo still at `20261104_0009`, with 23 draft lessons and zero published.

The two coach browser cases passed against the disposable service. One
ordinary learner completed the bakery scenario, requested an explanation,
reopened the summary and confirmed a second account received HTTP 404.
The voice case recorded the synthetic microphone input, received a real
Faster-Whisper Base transcript, played Piper audio generated from the real
Ollama reply, and found the saved turn in the shared transcript after reload.
The separate M08 browser suite passed all **seven** cases, including draft
denial, all six exercise formats and reviewer access.

## Manual browser run

In a terminal, start a disposable demo with:

```powershell
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py --serve-coach
```

The local frontend is `http://127.0.0.1:3012/login` and the API is
`http://127.0.0.1:8012/api/v1`. When the runner reports readiness, use a
second PowerShell terminal to copy each temporary credential and paste it
into its matching field before copying the next one:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m083_local.py --copy-coach-email
.\.venv312\Scripts\python.exe backend\scripts\m083_local.py --copy-coach-password
```

Open **AI Tutor → Conversation practice → Ordering at a boulangerie**. Start
text practice, choose a difficulty and correction timing, send a French
response, ask a question, finish and reopen the summary from History. Start
speaking from the scenario card to test the microphone and playback. Use
the shared transcript link to inspect saved text. Stop the local runner
with Ctrl+C.

## Remaining limits

The coach suggests corrections and distinguishes style from likely grammar
errors. Its suggestions still need human judgment. The medical situations
use authored language prompts. Deletion applies to standalone tutor
conversations. The existing speech and study history references protect
linked conversations and raw audio keeps its own deletion control.

The curriculum still needs independent review and a separate publication
decision. Manual testing with a physical microphone and personal browser
profile remains separate from the synthetic microphone test.
