# Milestone 06 verification

Verification completed on 3 November 2026. Milestone 07 was not started.

## Delivered behavior

The dashboard links to voice practice while retaining the text tutor. Voice practice uses the authenticated saved profile and CEFR level, offers the existing original scenarios, and saves private conversations. Recording requires an explicit microphone action. Learners can pause, resume, cancel, review, and submit a recording; tracks stop when recording ends or the page closes. Text input remains available when microphone access or speech services fail.

Transcripts show recognition status. Unusable or uncertain recognition does not automatically invoke the tutor. Successful turns retain the tutor text even if speech synthesis fails; audio can be retried without regenerating the answer. French audio has explicit playback controls and speed selection, with no autoplay. History survives refresh and login. Pronunciation targets come from authorized, versioned curriculum examples. Practice records recognized words and cautious guidance, with assessment marked unavailable and no acoustic score.

Raw learner audio storage is opt-in per recording. Private downloads recheck ownership, source authorization, expiry, and file presence. Existing name personalization and optional age-band storage remain in place; unnecessary identity fields are not supplied to speech or lesson prompts.

## Changed files

- `backend/app/speech/`: schemas, persistence models, bounded audio validation/decoding, ASR/TTS adapters, private inference worker, provisioning, storage/cleanup, voice orchestration, curriculum targets, and unavailable acoustic assessor.
- `backend/app/api/v1/speech.py`: authenticated speech, session, turn, audio, pronunciation, progress, and history endpoints under `/api/v1/speech`.
- `backend/app/config.py`, `main.py`, `ai/orchestrator.py`, `alembic/env.py`: configuration, router/lifespan integration, server-controlled French voice policy, and migration model registration.
- `backend/alembic/versions/20261102_0007_voice_learning.py`: additive schema revision.
- `backend/requirements.txt`, `requirements-speech.txt`, `Dockerfile.speech`, both Compose files, `.env.example`, `.gitignore`: optional isolated native inference deployment and private storage. Local worker secrets were generated separately for main and preview; they are not documented here.
- `frontend/lib/api.ts`, `speech.ts`, `speech-types.ts`, `components/voice-recorder.tsx`, `voice-practice.tsx`, six `app/voice-practice` pages, and dashboard: multipart transport, recording, conversation/history, reference and pronunciation screens.
- `backend/tests/test_speech.py`, `test_speech_decode.py`, `test_speech_postgres.py`, licensed `tests/fixtures/speech/`, `frontend/e2e/speech.spec.ts`: regression and integration coverage.
- `backend/scripts/ai_e2e_server.py`, `speech_e2e_server.py`, `speech_quality_smoke.py`, `speech_preservation.py`, `verify_speech_restart.py`: isolated test infrastructure and reproducible verification.
- `README.md`, `docs/architecture/voice-learning-system.md`, three `docs/speech/` guides, `docs/security/speech-data-privacy.md`, and this report plus JSON evidence.

## Migration and preservation

Revision `20261102_0007` follows `0006` and creates only `speech_sessions`, `speech_turns`, `speech_audio_assets`, `pronunciation_attempts`, and `speech_practice_progress`, with ownership, uniqueness, and unavailable-score constraints. It does not rewrite existing profile names or age bands. Fresh and populated isolated databases passed upgrade, downgrade, and re-upgrade checks. The populated test preserved the contents of all 47 pre-existing tables.

Both deployed environments report `20261102_0007 (head)` and six healthy services each, including private speech workers. Post-deployment fingerprints of all 47 existing tables are recorded in [preservation evidence](MILESTONE_06_PRESERVATION.json). Every table retained its row count. Main differs only in session metadata following authenticated use; preview differs only in lexemes following the existing startup importer. Other fingerprints, including profiles, registration age bands, progress and AI history, match the baseline. No existing data was restored or deleted to force a match.

## Executed checks

| Check | Observed result |
| --- | --- |
| Full core backend suite | 116 passed, 3 optional/dependency skips; two existing deprecation warnings |
| Final speech regression rerun after storage check | Passed |
| Native decoder suite in speech environment | 3 passed |
| Genuine PostgreSQL + local speech + Ollama pipeline | 1 passed; transcription, personalized French reply, WAV, logout/login persistence and private audio deletion |
| Controlled local-model quality fixtures | 10 completed; see [observations](MILESTONE_06_SPEECH_OBSERVATIONS.json) |
| Playwright regression suite | 16 passed, 1 optional M04 live test skipped |
| Frontend lint, typecheck, production build | Passed; all six voice routes included |
| Isolated API restart and session replay | Passed; persisted session resumed and duplicate request replayed |
| Fresh/populated migration round trips | Passed |
| Main/preview backend, frontend, speech image builds | Passed |
| Deployed main worker smoke | ASR/TTS healthy; human “bonjour” fixture returned uncertain French text; French synthesis produced a 109,612-byte WAV |

Playwright uses Chromium fake microphone hardware and injected inference. It verifies recording controls, denial/cancellation, track release, navigation, review/upload, persistence, fallback, pronunciation history, cross-user denial and draft access. These browser results are separate from the genuine model/PostgreSQL/Ollama checks. No physical microphone was activated by automation.

## Models and limits

Local CPU inference uses Faster-Whisper tiny, int8, and Piper `fr_FR-siwis-medium`. ASR revision: `d90ca5fe260221311c53c58e660288d3deb8d356`; voice revision: `e7229f7d33a10e145e109b886d661984201ac3c4`. Provisioning records individual SHA-256 checksums. No automatic model download occurs on request/startup. Licensing and attribution are documented in the setup guides and fixture attribution.

Defaults bound uploads to 5 MB and recordings to 30 seconds, validate decoded audio, limit concurrency and enforce process timeouts. Raw audio stays out of PostgreSQL. Provider failures preserve usable text. Tiny ASR can misrecognize speech and a brief human clip required an uncertain French retry; recognition is not evidence of pronunciation correctness. There is no validated phoneme assessor, numerical acoustic score, speaker comparison, or claimed pedagogical calibration.

## Physical microphone check still required

Open `http://localhost:3000/voice-practice` (preview: port 3001) with an isolated verified test account. Choose a scenario, allow the microphone, say “Bonjour, je voudrais une baguette, s'il vous plaît”, pause/resume, stop, and listen to the review before submitting. Confirm transcript review, French response playback/speed, refresh/history, and text fallback. Repeat with permission denied and with cancellation/navigation; the browser microphone indicator should stop. Leave raw-audio retention unchecked, then separately test opt-in retention and deletion. Confirm published pronunciation targets or use only an authorized administrator preview; no published target is fabricated to bypass review gates.

This hardware check is outstanding. The committed licensed human fixture and synthetic fixtures provide repeatable model checks without claiming a live microphone test.

Potential future work, without implementation here: independent French review/publication, broader real-speaker ASR evaluation, accessible physical-device trials, and a separately validated pronunciation assessor before any scoring UI.
