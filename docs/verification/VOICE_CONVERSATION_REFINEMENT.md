# Milestone 06 voice conversation refinement

Verified 3 November 2026. No new milestone was introduced.

## Findings and actual ASR comparison

The initial multilingual Tiny model can recognize the language correctly but still misrecognize connected French words and proper names. Language confidence is not word correctness. No expected introduction, learner name or reference sentence was supplied to ASR in this investigation.

Four recorded French introductions from the Canary Islands education authority were evaluated as excerpts of at most six seconds, alongside the existing human French greeting, public-domain human English greeting, a synthetic English sentence control, silence and seeded noise. These are local research samples, not additions to the curriculum. Attribution, source URLs, hashes and model revisions are in [source metadata](VOICE_REFINEMENT_ASR_SOURCES.json); the source recordings remain ignored local files. The publisher lists CC BY-NC-SA terms on its [resource page](https://www3.gobiernodecanarias.org/medusa/ecoescuela/recursosdigitales/2021/12/14/bonjour-je-mappelle/).

Compared CPU int8 Tiny and Base, each with beam sizes 3 and 5 under automatic detection, plus beam 5 with explicit French. Both retained VAD, word timestamps, temperature 0, no previous-text conditioning and no initial prompt. All 54 measured configurations/results are in [comparison evidence](VOICE_REFINEMENT_ASR_COMPARISON.json).

Observed differences included Tiny splitting the name Alexandra into two words, while Base returned the correct name. Base also recognized the phrase about being originally from Geneva that Tiny garbled. Base still spelled Isabelle as Isabel, and both models made errors in the longer food-preference excerpt. Increasing the beam did not consistently improve these cases. This small comparison is qualitative evidence, not a population WER benchmark, accent evaluation or calibration.

| Choice | Automatic beam-3 time on introduction excerpts | Result |
| --- | --- | --- |
| Tiny | 0.67–1.02 seconds | More errors in several connected phrases/names |
| Base | 1.66–1.89 seconds | Improved several phrases; still made spelling/word errors |

Base is selected in this workspace's local `.env` for both main and preview. Its revision is `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`; Tiny remains at `d90ca5fe260221311c53c58e660288d3deb8d356`. Base loads separate `asr-base/` weights and reports its real model name; changing the setting no longer merely changes a label. Beam 3 remains selected. Existing Tiny installations continue to use `asr/` when selected. No model is downloaded or substituted on a request.

The laptop had approximately 3.43 GiB free RAM during inspection, out of approximately 15.82 GiB usable system RAM. CPU inference was tested; no GPU claim is made. After real ASR, the deployed main and preview workers used approximately 230–235 MiB within their existing 2 GiB limits. This is an observation, not a guaranteed peak memory bound.

Silence, clipping, finite waveform/size/duration checks, automatic non-French detection and the existing uncertainty thresholds remain unchanged. Base recognized the human French greeting, and confidently rejected the human English greeting. Forcing French can still return English words, so it is not used to bypass the independent language decision. Proper names and accented/short/noisy recordings remain limitations. The user's specific microphone introduction was not available as retained audio; it was not recreated with an expected sentence and claimed as a successful recognition test.

## Explicit review and database provenance

Uncertain recognition stays editable and is never sent automatically. Clicking **Review recognized words as text** opens a review panel with immutable **Original recognized text**, an editable **Corrected sentence**, and **Confirm and send corrected sentence**. Cancellation sends nothing. Confirmation is a separate action, rather than a silent replacement by a guessed introduction.

`POST /api/v1/speech/sessions/{sid}/text` accepts optional `reviewed_turn_id`. The backend checks that the source is a nonempty uncertain turn owned by the learner in that session. It rejects cross-user/session references and client-supplied original-text fields. The source ASR turn and its transcription metadata stay unchanged. A new `user_confirmed` turn stores the accepted words in `transcript` and structured JSON `review` metadata containing `source_turn_id`, `original_text`, `confirmed_text` and `confirmed_at`. The response exposes this as `review`.

The input checksum includes the source ID as well as the confirmed words. Replaying the same request returns the same result; changing the source under that ID conflicts. The tutor sees only the learner-confirmed message, not the rejected recognition. History displays both versions after refresh. Audio failure preserves the confirmed words and tutor response. Existing unlinked text-fallback turns remain readable; no provenance is invented for older conversations.

No migration is required: this uses the existing structured JSON metadata and turn fields. Both environments remain at `20261102_0007`. No existing profile, name, progress or speech turn is rewritten. Read-only checks of the 47 pre-speech tables retained every row count; fingerprints differ only in main session metadata and preview lexeme timestamps after its existing importer ran. See [preservation evidence](VOICE_REFINEMENT_PRESERVATION.json). Speech-history preservation and new review provenance are additionally tested directly in the unit suite and real PostgreSQL integration.

## Voice tutor style

Voice now uses a dedicated CEFR policy rather than combining the text tutor's English-first A1 instructions with an appended French instruction. The voice branch removes the instruction to narrate general-model grounding; the application already shows grounding labels. The text tutor's policies and personalization remain unchanged.

A1 asks for familiar present-tense French, one or two short sentences and one relevant question. The validator bounds A1 French to 35 words and all voice replies to one question. It rejects internal profile/system/retrieval explanations before they are saved or synthesized. One optional short `English:` line follows the French; only the French portion reaches Piper. There is no hidden response rewrite or canned substitute: a rejected provider reply returns the existing safe unavailable response and can be retried.

Identity remains separate, with the bounded first-name hint only. The prompt forbids explaining how a name was obtained and forbids substituting a profile name for the name in a learner's introduction exercise. In the live introduction check, the learner exercise used Camille while the profile hint was Learning. The reply addressed Camille, stayed short, asked one question and produced audio without discussing the profile. That verifies the measured example, not universal linguistic quality.

## Checks executed

| Check | Result |
| --- | --- |
| Full core backend regression | **150 passed, 3 skipped**, two existing deprecation warnings |
| Native decoder, ASR policy and voice-style checks | **34 passed** |
| PostgreSQL + optional genuine Base/Ollama/Piper integration | **1 passed**; also tested injected uncertain review provenance in real PostgreSQL |
| Speech Playwright tests | **6 passed**; review uses a real API/database with explicit deterministic ASR/TTS injection |
| Frontend lint, typecheck, production build | Passed |
| Main/preview backend, frontend and worker builds | Passed |
| Docker health and native ASR | Six healthy services per environment; both workers report Base and recognize the human French fixture; main also rejects human English |

The live pipeline produced playable WAV data, persisted history through logout/login and verified private-audio deletion. It returned a short French question for the bakery sample. The introduction exercise produced a short reply addressing Camille with one question and playable audio. The captured live test log is local and not a production request log.

The native environment initially lacked the already-declared `langdetect` dependency; installing pinned `langdetect==1.0.9` corrected the environment, after which all 34 checks passed. No speech-language safeguard was weakened to satisfy a test.

## Changed files

- `backend/app/ai/prompts.py`, `orchestrator.py`: distinct voice CEFR/style instructions and validation before persistence/TTS.
- `backend/app/speech/schemas.py`, `voice_orchestrator.py`, `backend/app/api/v1/speech.py`: typed review provenance, authorization, immutable source and idempotency.
- `backend/app/config.py`, `speech/faster_whisper_provider.py`, `speech/worker.py`, `speech/provision_models.py`: explicit Tiny/Base selection, separate weight paths, selected-model readiness and provisioning manifests.
- `frontend/lib/speech.ts`, `frontend/components/voice-practice.tsx`: review payloads, editing/confirmation and original-versus-confirmed history.
- `backend/tests/test_speech.py`, `test_speech_asr.py`, `test_speech_postgres.py`, new `test_voice_style.py`, `frontend/e2e/speech.spec.ts`, `backend/scripts/speech_e2e_server.py`: regression and integration coverage.
- New `backend/scripts/compare_french_asr.py`, this report and three linked evidence JSON files; updated `.env.example`, speech setup, architecture and tutor-prompt documentation. Local `.env` selects Base; downloaded weights and source recordings are ignored local assets.

## Retest in the browser

Hard refresh `http://localhost:3000/voice-practice` (preview port 3001), start a new conversation and record your introduction. For uncertain recognition, open review, edit the sentence and explicitly confirm. After refresh, verify the original recognized words and your confirmed words are both visible. The tutor should answer briefly in French with one question; any short English explanation follows it. Playback should contain the French portion only. Old saved turns retain their original text/status and are not reprocessed on refresh.

No physical microphone was activated by automation; Playwright used fake microphone hardware. Retest with your microphone and accent remains useful, especially for names. No pronunciation scoring, fine-tuning, automatic expected-sentence replacement or Milestone 07 work was added.
