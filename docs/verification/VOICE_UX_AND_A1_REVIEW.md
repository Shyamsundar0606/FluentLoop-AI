# Voice UX and A1 review verification

Date: 3 November 2026. Scope: refinements to existing Milestones 01–06 only.

## Result

Uncertain speech opens immediately as an editable learner bubble. The original ASR text remains visible, with **Confirm and send** and **Record again** beside the editor. Nothing sends to the tutor until explicit confirmation. Confirmed messages and tutor replies use the existing white/purple chat design; original recognition is available under **Recognition details**. The microphone becomes compact after the first turn and remains sticky while browsing the conversation.

All ten A1 lessons remain **draft**, with no publication or claimed independent review. The [lesson-by-lesson readiness report and blank reviewer checklist](../content/reviews/A1_REVIEW_READINESS.md) identify actual editorial, data-link and licensing blockers.

Follow-up completion checks are recorded below. The full backend suite now runs with native dependencies and both isolated PostgreSQL integration databases: **159 passed, zero skips**. The [concrete correction proposals](../content/reviews/A1_PROPOSED_CORRECTIONS.md) give reviewers suggested replacements and a data-link reconciliation plan while preserving all existing draft content.

## Changes and files

| File | Change |
|---|---|
| `frontend/components/voice-chat.tsx` | Chronological chat renderer, inline review form, original recognition disclosure, truthful edited indicator, compact tutor playback and collapsed learning context. |
| `frontend/components/voice-practice.tsx` | Automatically select the latest uncertain recording for review, preserve unsent edits across refreshes in the mounted session, explicit confirmation/re-record callbacks, separate ordinary text fallback, compact microphone dock. |
| `frontend/components/voice-recorder.tsx` | Optional compact presentation and an imperative re-record action invoked by an explicit user click; existing permission, recording, cancellation and privacy controls retained. |
| `frontend/app/globals.css` | Compact conversation and microphone styles, responsive spacing, purple learner/white tutor bubbles. |
| `frontend/lib/speech.ts` | Optional additive `review.edited` response typing for rolling compatibility. |
| `backend/app/speech/schemas.py` | Review responses include the edited boolean. |
| `backend/app/speech/voice_orchestrator.py` | Persist the edited boolean in the existing review JSON; derive it for old rows on read without rewriting history. |
| `backend/scripts/a1_review_audit.py` | Read-only source/deployed curriculum comparison and reviewer evidence export. |
| `backend/tests/test_speech.py` | Edited/unchanged confirmation, legacy-read behavior and immutable-source assertions. |
| `backend/tests/test_speech_postgres.py` | Real PostgreSQL edited provenance; live actual ASR → deterministic uncertain classification → explicit corrected text → real Ollama/Piper → saved history after login. Wait for real rate-limit retry window if the extended sequence reaches its quota. |
| `backend/tests/test_a1_review_audit.py` | Detect missing linked examples and wrong keys, establish clean disposable-fixture comparison, verify no audit DML or publication. |
| `frontend/e2e/speech.spec.ts` | Immediate editor/focus, double-click single submit, original/confirmed persistence, edited/unchanged indicators, re-record/cancel, chat ordering, replay/private deletion, responsive review screenshots. |
| `frontend/e2e/milestone04-live.spec.ts` | Align existing dashboard metric selectors and exact sign-out locator with the preserved redesign. |

Supporting artifacts: this report, `docs/content/reviews/A1_REVIEW_READINESS.md`, `A1_REVIEW_AUDIT_MAIN.json`, `A1_REVIEW_AUDIT_PREVIEW.json`, `VOICE_UX_PRESERVATION.json`, `VOICE_UX_NATIVE_GUARDS.json`, `VOICE_UX_DOCKER_SPEECH.json`, backend/live test logs, and `docs/verification/voice-ux/` screenshots.

## Before and after

Previously a learner had to open the separate review controls and the page repeated several large recognized/confirmed/response sections. Now the latest uncertain recording receives focus in the conversation automatically, prefilled with exactly the recognition result. The instruction is “Check what we heard and correct any mistakes.” A failed recognition is never silently replaced by a presumed French sentence.

Confirming creates the existing separate `user_confirmed` turn with source-turn ID, original text, confirmed text, timestamp and `edited`. The original turn stays immutable in PostgreSQL. A single learner bubble displays the confirmed text, and the original moves into Recognition details. Changed text gets **Edited transcript**; unchanged confirmation does not. The frontend busy/ref lock and existing backend request UUID/checksum/idempotency remain in force.

Record again dismisses the current editor locally and starts capture only from that button click. It does not submit an abandoned edit, delete the recording's stored recognition, or grant audio retention consent. The learner may cancel capture and reopen the old recognition from its details. A page reload can reoffer the still-unconfirmed latest recording because dismissal is intentionally not stored as a destructive server action.

Regular text fallback remains independently available. Existing private input replay is inside Recognition details, and tutor French playback remains below its reply. Original source rows hidden by their confirmed replacement remain in the database and API; this is presentation deduplication only.

## Tutor presentation and safeguards

No ASR thresholds, language detection/VAD settings, model selection, prompt text, retrieval rules or speech validation were changed. The existing CEFR-aware voice prompting and validation retain the 35-French-word A1 limit and at most one French question. `ChatText` continues to separate optional `English:` explanations. The existing French-only speech text is synthesized; playback does not speak the English explanation. Live integration and native response-style/audio tests exercise these paths.

Tutor technical context remains collapsed. Authenticated profile personalization, first-name handling, text-tutor conversation memory and draft-preview permissions use the existing backend paths. This work does not introduce client identity instructions or send email, credentials, tokens or age information to Ollama.

## A1 results and blockers

Both source and deployed content were inspected: structure, 83 vocabulary occurrences/78 normalized identities, translations, grammar/rules/examples, dialogues, five exercises per lesson and answer keys. Source schema validation passes and all 50 imported keys structurally match the source. Main source/deployed comparison passes for 8/10 lessons and preview for 9/10; aggregate audit is **false** and must not be mistaken for publication readiness.

- Main A1-003 has an extra `basic-sentence-order` grammar topic. Preview matches the expected topic set.
- Both A1-009 deployments contain two examples without vocabulary-example links, making them unreachable through lesson vocabulary joins. An isolated clean import reproduces this gap.
- Specific editorial findings include inaccurate `dix`, `mon` liaison and `voudrais` pronunciation explanations, an ambiguous `livre` exercise, misleading double-l guidance and listening/objective or scaffold gaps. Details and primary language references are in the readiness report.
- Source licensing still explicitly asserts no publication license, source URL is absent, attribution review is pending, and every independent review remains pending.

Three packets (002, 006, 007) are technically ready to begin external review with scaffold notes. Seven have correction recommendations or technical blockers. **None has publication approval.** No source JSON, draft wording, review approval template or publication status was edited, and the publisher was never invoked. Existing ordinary-learner hiding and authorized preview permissions remain in place.

## Verification results

| Check | Actual result |
|---|---|
| Full backend pytest | **159 passed, 0 skipped**, 2 existing dependency deprecation warnings, in the follow-up native environment with both isolated PostgreSQL URLs. The earlier core-only run was 153 passed/3 skipped; the missing native decoder and PostgreSQL checks have now been executed. [JUnit evidence](VOICE_UX_COMPLETION_TESTS.xml). |
| Native speech checks | **34 passed**: decoding, ASR safeguards and voice-style/TTS validation. |
| Live speech/PostgreSQL integration | **1 passed** in 60.66 seconds with real local Faster-Whisper Base CPU/int8, Ollama `llama3.2:3b`, Piper SIWIS French, and isolated PostgreSQL `fluentloop_m06_verify`. |
| Additional real text-tutor integration | **1 passed** in 57.20 seconds with real Ollama `llama3.2:3b` and isolated PostgreSQL `fluentloop_m05_verify`: tutor/grammar/correction modes, roleplay, persisted history after login and a follow-up. The structured correction changed `Je suis 24 ans.` to `J'ai 24 ans.`. [JUnit evidence](VOICE_UX_TEXT_TUTOR_LIVE.xml). This is a regression/inference check, not certification of every generated explanation. |
| Frontend ESLint | Passed. |
| TypeScript | Passed. |
| Production build | Passed, all 33 pages generated, static/partial routes completed. |
| Speech Playwright | **8 passed** across two serial groups: capture/pause/stop, immediate review/confirmation, double-click guard, re-record, unchanged/changed flags, chronological chat, replay/private deletion, history, permission failure, cross-owner denial, draft target denial, microphone track cleanup. |
| Other frontend workflows | **12 passed**, including actual isolated registration/email verification/onboarding/profile update, actual text-tutor persistence and owner isolation, mocked learning/text-tutor states, and responsive navigation/focus/appearance checks. One optional live-learning case initially skipped pending its dedicated account/option environment; separate result below. |
| Additional live learning workflow | **1 passed** after supplying fresh isolated admin/learner accounts and actual database exercise IDs: all ten draft labels in authorized preview, actual server grading, idempotent answer replay, wrong-answer feedback, reload/completion, 80% result, logout/login persistence, and ordinary-learner/cross-owner denial. Updated old metric selectors and waited for the dashboard route before locating its visible sign-out button, accounting for Next.js retained route trees. **Total browser coverage: 21 passed** across the groups. |
| Responsive review | Passed at widths 320, 390 and 1440: no horizontal overflow, focused editor and confirmation visible, microphone in viewport with ≥44px target. Screenshots inspected at desktop and mobile. Existing redesign suite also checks 20 route/width combinations. |
| Main and preview Docker | Backend/frontend image builds and recreation passed in both stacks. All **12 services healthy**: each stack's backend, frontend, PostgreSQL, Redis, Mailpit and private speech worker. HTTP ready/pages return 200. |
| Migration | None added. Both databases remain at `20261102_0007`. |
| Read-only A1 audit | Completed against both databases; draft-only status verified, actual drift reported as blockers rather than “fixed” by weakening the audit. |

[Native fixture evidence](VOICE_UX_NATIVE_GUARDS.json) also records actual decoded sample rate, duration, RMS, peak, codec/container and inference: human French Ogg and the same waveform encoded as browser-style WebM/Opus both produce `bonjour`; known English is `non_french`, and silence is `no_speech`. [Docker speech evidence](VOICE_UX_DOCKER_SPEECH.json) verifies actual French fixture transcription and RIFF TTS from each backend through its private worker: main generated 82,988 bytes and preview 76,332 bytes. Worker authentication stays internal; no worker tokens are exported.

The live uncertainty branch explicitly injects only the uncertain **classification** after real decoding/transcription of the human French fixture. Native ASR returned `bonjour` as transcribed. The text remains actual ASR output, and no expected sentence replaces it. The test then explicitly confirms `Bonjour, je m'appelle Camille. J'habite à Paris.`, observes that sentence in the real Ollama request, downloads RIFF French TTS, and reloads the review from PostgreSQL after logout/login. In the successful run, corrected-turn audio was **238,636 bytes**. This proves the branch end to end without claiming that a known fixture naturally triggers uncertainty every run.

Earlier live attempts exposed the real quota on final audio deletion and one transient model response rejected by the existing tutor validator (503). Validation was preserved; the final run passed. The test now waits for the quota's actual Retry-After window. Browser media tests use Chromium's fake microphone with the explicitly guarded isolated API and deterministic inference; they do not claim to test a physical microphone or real model generation inside Chromium. Real inference is checked separately as described above.

## Security, privacy and preservation

CSRF, session authentication, verification, password hashing, quotas, cross-user ownership, upload limits and private audio authorization are unchanged. Original and confirmed text stay distinct account-owned records. Review metadata is additive JSON in the existing speech architecture; old rows derive edited status at read time. Audio opt-in, track release on cancel/unmount, expiry and private deletion remain available. No validation was disabled.

[Preservation evidence](VOICE_UX_PRESERVATION.json) fingerprints **52 tables in each deployed database**, including speech tables. All row counts match before/after. In each stack 51/52 full-table hashes match. Main `user_sessions` changed while an existing session's last-used timestamp advanced; no session rows were added/deleted by this work. Preview `lexemes` changed when its existing startup import refreshed the `avoir` row's updated timestamp. The read-only lesson comparison is unchanged after restart. Because the baseline stores table hashes rather than every column's before-image, it cannot establish a complete per-field diff of those two tables.

User records/password hashes, profiles/preferences, learning progress/attempts/results, AI conversations/messages, speech sessions/turns and all other table hashes are unchanged. No volume was reset, no real account was used for automated mutation, no learner records were deleted, and all ten lessons remain draft. Separate synthetic accounts and their progress/conversations exist only in the isolated test database.

## Browser retest

1. Open main `http://localhost:3000`, or authorized draft preview `http://localhost:3001`. Reload the page after the updated containers start; sign in to the intended account. Preview access remains role-gated.
2. Select **Speak → Start Voice Conversation**. Tap the microphone, allow permission, say a short French sentence, stop and listen to the local recording if desired. Retention is off by default and can be enabled only through Recording options & privacy.
3. Submit the recording. A clear transcription may go directly to the tutor through the existing path. If recognition is uncertain, the correction field opens immediately with the exact original text. Do not expect every recording to enter review.
4. Correct the text and choose **Confirm and send**. Verify one learner bubble, an Edited transcript badge only when changed, and one tutor reply. Expand Recognition details to compare original and confirmed data. Repeated clicks must not create another turn.
5. On another uncertain recording choose **Record again**. Verify recording begins, no tutor request is made for the discarded edit, and Cancel recording switches the microphone off. The original remains reviewable under its details.
6. Play tutor audio. It should read the displayed French reply; optional English remains separate. Check private input replay/deletion from Recognition details if retention was chosen.
7. Refresh, open Speak history, then sign out/in and reopen the session. Confirm chat order, corrected text, original recognition details and edit badge persist. Generated audio can expire after the existing retention period; transcript history remains.
8. At a narrow mobile width, focus and edit the sentence, confirm it, scroll a longer chat, and check the sticky microphone, navigation and keyboard focus. Actual mobile permission prompts and soft-keyboard behavior require device testing.
9. As an ordinary learner check Learn: unpublished lessons stay hidden. In authorized preview inspect all ten draft labels and use the linked reviewer packet; do not publish until genuine independent approvals are recorded against the final content version.

## Known limits

ASR may still mishear French names, short introductions or noise. This refinement improves honest review and does not claim an accuracy gain or alter the existing model comparison. Only the latest unconfirmed uncertain turn opens automatically; older uncertain recordings remain explicitly reviewable. Unsent text is component state and is not a durable draft across full page reloads. Browser automation does not cover physical hardware or the mobile soft keyboard. Ollama can still produce rejected/failed responses; guards and retry behavior remain active. Current curriculum drift and editorial/rights blockers require a separately reviewed correction and genuine human sign-off before publication. Milestone 07 was not started.

## Follow-up completion audit

The repeated attachment matches the original brief. Existing voice implementation, frontend checks and browser evidence remain applicable; this follow-up closed the previously skipped backend checks and made the A1 correction packet concrete.

- The first expanded test run exposed a stale **isolated** `fluentloop_m05_verify` database at migration `20261102_0005`, missing `registration_age_band`. Applied the existing additive migrations 0006 and 0007 only to that test database; no new migration was authored. The final full-suite rerun passed all 159 tests with zero errors/failures/skips.
- Ran the optional real Ollama text-tutor branch separately; it passed. Real speech integration and browser tests are documented in their existing rows above and were not relabeled as newly rerun tests.
- Repeated both read-only deployed A1 audits: each still has 10 draft lessons and 0 published; the previously documented A1-003/A1-009 issues remain. The proposed corrections document includes exact editorial replacements and an explicit A1-009 association plan, without applying changes or inventing reviewer approval.
- Rechecked main/preview Docker: all 12 services running and healthy. No app-source changes or deployment were necessary in this follow-up. No main/preview database writes, volume resets, session revocations or learner-record deletions were performed by these completion checks.

### Brief completion matrix

| Phase | Status and evidence |
|---|---|
| 1. Uncertain transcript review | Implemented and browser/backend verified: immediate editable original, explicit confirmation, re-record, immutable original, separate confirmation/edited flag and duplicate protection. |
| 2. Voice chat | Implemented and verified: chronological purple/white bubbles, recognition details, original private replay, French playback, accessible compact microphone and responsive screenshots. |
| 3. Tutor presentation | Existing CEFR prompts/guards preserved; French/English separation, audio generation and real inference verified. |
| 4. A1 review preparation | Complete: all ten lessons inspected, read-only integrity exports, per-lesson triage, blank independent-review checklist and concrete correction proposals. Actual corrections/publication remain subject to the brief's review requirements. |
| 5. Automated testing | Full backend now 159/159 with no skips; additional real text-tutor check passed. Previously completed native/live speech, lint, typecheck, production build and 21 browser cases remain recorded above. |
| 6. Documentation | Complete: changed files, behavior, tests, security/preservation evidence, limitations, reviewer materials and browser retest instructions linked in this report. |

Outstanding external work is identified rather than silently marked done: independent French/pedagogy/answer and separate licensing decisions, approved reconciliation/content revisions, and physical-device/soft-keyboard manual checks. No lessons have been approved or published by this follow-up.
