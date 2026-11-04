# French recognition investigation and fix — 3 November 2026

## Root cause and scope

The failure is in the ASR language decision policy, rather than an identified browser encoding or upload corruption. Multilingual Whisper tiny sometimes assigns the wrong language to genuine short French speech. Previously, any non-French prediction on a recording lasting at least three seconds was immediately labelled `non_french`, even if language confidence was very low. The constrained French recovery path was available only for files shorter than three seconds. Recording length included waiting/silence, so the same spoken word received different treatment depending on when Stop was pressed.

Read-only inspection of the two existing failed turns found:

| Recording | Codec/container | Duration | Automatic language | Probability | Signal flags |
| --- | --- | --- | --- | --- | --- |
| Earlier failure | Opus/WebM | 13.26 s | Portuguese | 0.38375 | None |
| Later failure | Opus/WebM | 7.74 s | Urdu | 0.82014 | None |

Neither recording was retained. Their original waveforms, voiced durations and forced-French results cannot be reconstructed. The low-confidence Portuguese decision demonstrates the erroneous hard rejection policy. The higher-confidence Urdu case remains unverified: this fix deliberately retains the 0.8 rejection boundary instead of lowering it merely to accept that recording. Do not claim both original recordings have been successfully recognized.

## Measured reproduction

The committed human French fixture is Vion Nicolas's “bonjour”. Automatic tiny inference labelled it Russian; explicit `language="fr"` recovered “Bonjour !”. The original file is 1.2 seconds. Adding ordinary silence yields a 5.2-second file containing 1.6 seconds after VAD padding. Both WAV and Opus/WebM versions were rejected before the fix, despite valid decoded waveforms. After the fix they yield an explicitly uncertain French hypothesis for learner review.

| Decoded fixture | Rate/channels | Samples / duration | RMS | Peak |
| --- | --- | --- | --- | --- |
| Human original Ogg/Vorbis | 16 kHz / mono | 19,200 / 1,200 ms | 0.15086 | 0.80020 |
| Padded WAV | 16 kHz / mono | 83,200 / 5,200 ms | 0.07246 | 0.80017 |
| Padded Opus/WebM | 16 kHz / mono | 83,200 / 5,200 ms | 0.07253 | 0.78462 |

The signal is neither quiet nor clipped. Decoding preserves length, finite float32 samples and signal level. There is no evidence to justify changing PyAV resampling or microphone constraints.

A separate Chromium capture used its genuine `getUserMedia`/`MediaRecorder` implementation with a controlled WAV fake microphone input, the application's mono/echo-cancellation/noise-suppression constraints, 64 kbps Opus, and 250 ms chunks. It produced a 61,295-byte `audio/webm;codecs=opus` recording; all tracks ended after Stop. Real ASR returned `transcribed` French on this file, with word errors. This verifies browser encoding, not a physical microphone test. Repeated speech in this capture comes from Chromium looping the controlled input.

The browser sends a Blob using FormData without overriding its multipart boundary. FastAPI reads bounded 64 KB chunks, validates magic bytes and forwards unchanged binary content to the private worker. PyAV decodes supported codecs and resamples to mono float32 at 16 kHz. Unsupported codecs, empty/corrupt files, oversized uploads, excessive duration, nonfinite data, silence and clipping safeguards remain unchanged.

## Correction

`backend/app/speech/faster_whisper_provider.py` now uses the existing 0.8 confidence boundary consistently: a lower-confidence non-French prediction may receive a French-constrained retry regardless of total recording length. The result remains `uncertain`; forced French's reported probability of 1 is never used as independent evidence of French. Confident non-French remains rejected. VAD-empty noise now returns `no_speech` before interpreting meaningless language predictions.

No VAD or recognition confidence thresholds were relaxed. Silero VAD remains enabled with the installed Faster-Whisper 1.2.1 defaults (threshold 0.5, silence separation 2,000 ms, speech padding 400 ms). Beam size 3, temperature 0, no prior-text conditioning, word timestamps, no-speech and average-log-probability checks are retained. Upstream documents the distinction between automatic and explicit language selection in [the pinned Faster-Whisper implementation](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py).

`frontend/components/voice-practice.tsx` explains that uncertain words have not reached the tutor and provides **Review recognized words as text**. It fills and focuses the existing editable fallback; the learner must still click **Send text instead**. No uncertainty is silently promoted to recognized French. A short human English “hello” produced an uncertain “Hello.” hypothesis and was not accepted; a clear English sentence was confidently detected as English and remained `non_french`. Forcing French alone did not make that sentence French, confirming why the independent language check must remain.

## Verification

- Core backend: **131 passed, 3 optional/dependency skips**, two existing deprecation warnings.
- Native decoder and ASR policy suite: **19 passed**. Includes real Opus resampling, signal preservation, ambiguous short/padded/long inputs, 0.8 boundary, confident non-French, VAD-empty noise, silence/clipping, unreliable/empty segments and unchanged clear French acceptance.
- Real local tiny inference: nine controlled fixtures with automatic-versus-explicit French comparisons; status assertions passed. Human French and public-domain human English fixtures are attributed in `backend/tests/fixtures/speech/ATTRIBUTION.md`. Additional French/English sentence inputs are synthetic controls, not human-speaker calibration.
- Frontend lint, typecheck and production build passed.
- Speech Playwright suite: **6 passed**. Includes explicit review with zero text POSTs until the learner presses Send, then one edited text submission. An initial mock URL missed the history query parameter and was corrected; existing history required disambiguating repeated feedback labels. An isolated test-server configuration initially excluded development-only draft targets; it was corrected without changing production gates. Repeated runs encountered the real login limiter, so the isolated in-memory test server was restarted. No production rate limit was changed.
- Main and preview images rebuilt and services healthy; deployed private worker returned `transcribed` for Chromium French, `uncertain` for short human French/English and `non_french` for the clear English sentence.
- No schema migration. Both environments remain at `20261102_0007`. Read-only fingerprints of 47 existing tables per environment retain all row counts. Changes are limited to main session metadata and preview lexeme timestamps from the existing startup importer. Other existing content, names, age bands, progress and AI data match. See [preservation fingerprints](SPEECH_FIX_PRESERVATION.json).

Evidence: [before comparisons](SPEECH_RECOGNITION_BEFORE.json), [after comparisons](SPEECH_RECOGNITION_AFTER.json). The before set predates the two added English-human/browser controls. Reproduce native checks from the repository root:

```powershell
$env:PYTHONPATH = 'backend'
$env:SPEECH_MODEL_PATH = (Resolve-Path .speech-models).Path
$env:OPENBLAS_NUM_THREADS = '2'
.\.venv-speech\Scripts\python.exe backend/scripts/diagnose_speech_recognition.py --output docs/verification/SPEECH_RECOGNITION_AFTER.json
```

The diagnostic uses only named fixtures and local test files; it never reads learner recordings. Optional `.speech-models/test-en.wav` was generated with Windows Microsoft David; `.speech-models/test-fr.wav` used the installed French Piper voice. These ignored local files are not downloaded automatically or required by production.

Changed implementation/test files: `backend/app/speech/faster_whisper_provider.py`, `backend/tests/test_speech_asr.py`, `backend/tests/test_speech_decode.py`, `backend/scripts/diagnose_speech_recognition.py`, `backend/tests/fixtures/speech/en-us-hello.ogg` and `ATTRIBUTION.md`, `frontend/components/voice-practice.tsx`, and `frontend/e2e/speech.spec.ts`. Documentation/evidence changes are this report, the three linked JSON files, `docs/architecture/voice-learning-system.md`, and `docs/speech/faster-whisper-setup.md`. Browser recording, upload/decoder implementation, prompts, authentication and database schema were not modified.

## Exact browser retest

1. Open `http://localhost:3000/voice-practice` (preview: `http://localhost:3001/voice-practice`) and hard refresh with Ctrl+F5. Sign in using your existing account.
2. Start a new voice conversation, click **Record French**, and allow microphone access.
3. Say a complete French sentence, for example “Bonjour, je voudrais une baguette, s'il vous plaît.” Stop and replay it, then click **Submit recording**.
4. Clear recognition should show your words and a tutor reply. If recognition is uncertain, click **Review recognized words as text**, correct any errors, then click **Send text instead**. A tutor reply must not appear before that explicit submission.
5. In a new attempt, say “Bonjour” with a pause before Stop. A low-confidence language prediction should now yield reviewable uncertain words instead of being hard-rejected solely because the recording exceeded three seconds.
6. Test silence and a clear English sentence. Silence should produce no speech; confidently detected English should remain rejected and must not invoke the tutor.

Previously saved failed turns retain their original status; refreshing does not rerun inference. Make a new recording/request. If a fresh French recording is still `non_french`, preserve and provide that specific audio for comparison rather than assuming another threshold should be lowered. You may explicitly opt into temporary private retention for that attempt; default retention remains off. The 82% Urdu-labelled original cannot be verified without a new sample.
