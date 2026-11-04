# FluentLoop AI frontend redesign — verification

Completed as a visual/usability refinement of Milestones 01–06 on 3 November 2026. No Milestone 07 features, backend logic changes or migrations were introduced.

## Design and navigation

White/light-gray surfaces, restrained purple accents, dark navy text, light borders, rounded panels and one spacing/type system replace the gradient-heavy foundation UI. The public landing page now describes French learning rather than infrastructure. Existing dark-mode controls remain available.

There is one shared primary navigation: **Home, Learn, AI Tutor, Speak, Profile**. Desktop uses a compact sidebar; mobile uses the same five links in a bottom bar. Section navigation groups existing courses/vocabulary/grammar/progress, tutor conversations/history/recommendations, speaking/pronunciation/history, and profile/settings. All existing routes are retained. Onboarding keeps its focused six-step layout. Contextual lesson/course back links and save/exit actions remain available.

Home greets the authenticated learner by first name, shows the saved daily goal and real PostgreSQL-backed learning progress, and offers continuing lessons and two practice shortcuts. It does not invent streaks, completed minutes or course completion. Course availability and empty states still respect server permissions. Settings now refreshes the authenticated profile after saving preferences, so the shared level/goal updates during client navigation without requiring a reload.

## Voice refinement preserved

The existing MediaRecorder capture, MIME selection, request UUIDs, abort, pause/resume and track-release logic is retained. The primary recording control is 104 px, with visible active state, timer, stop and cancel. A completed recording has review playback, **Record again** and **Send recording**. Processing says **Understanding your French…**.

Pause/resume and explicit private-replay opt-in are under **Recording options & privacy**. The default remains unchecked and the discard policy is visible outside the panel. **Text fallback & conversation options**, per-audio speed/deletion options, service information and detailed privacy text are expandable. Unavailable speech services still show a visible warning. Native audio controls remain available inside audio options, alongside the new explicit Play control; autoplay is disabled.

Uncertain words are never submitted automatically. **Review recognized words as text** opens the correction panel, shows **Please check what we heard**, keeps the original words visible, focuses the editable sentence and requires **Confirm and send corrected sentence**. The existing `reviewed_turn_id` request and backend `review` response are unchanged. History still separates original recognition and learner-confirmed text. The browser regression checks zero text submissions before confirmation and verifies the source ID and confirmed words after refresh.

Pronunciation keeps authorized French targets, translation, reference playback, recording and saved recognition feedback. The unavailable acoustic-assessment message remains honest; no confidence-derived score was added.

## Tutor, lessons and accounts

Tutor messages use compact user/tutor bubbles, a clear composer, small level/status treatment and collapsible conversation options/history. Optional `English:` explanation text is visually separated. Grounding details remain accessible, with draft warnings visible before interaction. Sources, correction feedback, archive, rename, retry and older-message loading remain available.

Course/lesson pages use white panels instead of gradient headers. Draft badges retain readable contrast. Learning-session version information is secondary, while the level, exercises, grading feedback, progress and exit controls remain visible. Course-library empty states do not fabricate published content.

Registration keeps full name, optional age, email, password and confirmation, including validation and age-band disclosure. Onboarding does not ask for the registered name again. Profile editing, preferences, session management, sign-out and account deactivation are retained. Names continue to come from authenticated API state, not localStorage.

## Files and shared components

New components:

- `frontend/components/app-shell.tsx`: shared sidebar, five destinations, grouped links, account controls, saved-level indicator and skip link.
- `frontend/components/ui.tsx`: native SVG Icon, PageHeader, Button, Card, EmptyState and ChatText.
- `frontend/e2e/redesign.spec.ts`: responsive navigation, widths, focus, appearance, reduced motion and microphone target checks.

Reused/refined components:

- `auth-provider.tsx`: preserves ProtectedPage authentication while applying AppShell.
- `auth-shell.tsx`: shared forms, existing input styles and status/error messages.
- `voice-recorder.tsx`: presentation changes around the existing capture/upload lifecycle.
- `voice-practice.tsx`: recording focus, explicit audio playback, review visibility and secondary options.
- `tutor-shell.tsx`: removes duplicated navigation and groups privacy details.
- Existing ThemeToggle, BackendIndicator, API, curriculum, learning, speech and authentication clients remain in use.

Pages/configuration changed:

- `frontend/app/page.tsx`, `dashboard/page.tsx`, `globals.css`, `layout.tsx`.
- `ai-tutor/page.tsx`, `ai-tutor/[conversationId]/page.tsx`.
- `courses/page.tsx`, `courses/[courseId]/page.tsx`, `lessons/[lessonId]/page.tsx`, `learning/sessions/[sessionId]/page.tsx`.
- `profile/page.tsx`, `settings/page.tsx`, `progress/page.tsx`, `grammar/page.tsx`, `vocabulary/page.tsx`.
- Authentication, registration, verification, recovery, onboarding, tutor subpages and all speech routes also receive the shared shell/form/visual styling without replacing their route logic.
- `frontend/next.config.ts`: hides the development badge that overlapped mobile navigation; compile/runtime errors still surface.
- Updated `frontend/e2e/auth-flow.spec.ts`, `ai-tutor.spec.ts`, `speech.spec.ts`, and `frontend/README.md`; this report and linked JSON/PNG evidence.
- `frontend/.gitignore` excludes local Playwright traces/reports from source control.

No backend application files, database schemas, API contracts, model selections, curriculum, password handling or security limits were changed. No package dependency was added for the design; icons use native SVG. Existing package changes from earlier work were retained.

## Responsive and accessibility checks

Playwright checked 320, 390, 900 and 1440 px widths across Home, Learn, AI Tutor, Speak and Profile. It asserted exactly five primary destinations, a current destination, visible headings, no horizontal document overflow, a microphone target of at least 100 × 100 px, keyboard skip-to-content focus, dark appearance and reduced-motion CSS. Mobile section links can scroll horizontally within their own navigation bar; the document does not overflow.

Forms keep native labels, password autocomplete/visibility controls, required/optional semantics and visible validation. Status/error announcements and the live message list remain. Focus is visible; transcript review expands and receives focus after rendering. The active recording state is conveyed through text/timer and a stop control as well as color. Stop/cancel remain available while options are collapsed. No physical microphone was activated automatically.

Screenshots were visually inspected. This is targeted accessibility verification, not a claim of a complete WCAG audit or physical-device/browser certification.

## Test results and baseline

| Check | Result |
| --- | --- |
| Baseline lint/typecheck | Passed before redesign |
| Baseline workflow coverage | 17 passed across serial/isolated reruns; 1 optional live M04 test skipped |
| Final workflow coverage | **19 Playwright tests passed**, 1 optional live M04 test skipped, across isolated serial groups |
| Core backend regression | **150 passed, 3 optional/dependency skips**, two existing deprecation warnings |
| Frontend lint/typecheck/production build | Passed on final sources |
| Genuine browser speech pipeline | Passed with Base ASR, Ollama `llama3.2:3b`, Piper and real private WAV playback |
| Main/preview frontend image build and health | Passed; only frontend containers were replaced |

Workflow coverage includes registration validation, optional age, email verification/resend, login/rate-limit feedback, onboarding, first-name/profile updates, all six levels, client-side preference refresh, logout/session isolation, lesson resume/server grading/results, tutor questions/corrections/roleplay/history/archive/retry/permissions, microphone capture/pause/review/submission, uncertain correction persistence, pronunciation/reference audio/history, private replay opt-in/speed/deletion, denial/cancellation and track release during navigation.

The browser regression API uses the existing guarded `fluentloop_m06_verify` database and explicitly injected providers. Browser recording uses Chromium fake microphone hardware. These deterministic checks are separate from the genuine speech run below.

Initial parallel baseline checks had laptop timing failures and a Docker-only mail hostname; serial checks and host-local SMTP corrected the test setup. Combined groups can reach the unchanged login/speech rate limits, so they were run against fresh isolated test processes rather than weakening limits. Next's cached hidden routes required visible/exact selectors. A stale dev stylesheet disappeared after restarting the dev server; screenshot and deployed-style checks subsequently verified the real layout. The first live run was interrupted by a formatting hot reload and was rerun successfully against stable sources.

Reproduction uses an isolated API on 8016 with frontend origin `http://127.0.0.1:3016`, host SMTP `127.0.0.1:1025`, development-only draft preview enabled for the test administrator, and existing guarded test accounts. Set `PLAYWRIGHT_BASE_URL`, `PLAYWRIGHT_API_BASE_URL`, `AI_E2E_REAL_API=1`, `SPEECH_E2E_REAL_API=1` and optionally `UI_SCREENSHOTS=1`. Run serial groups; restart only the isolated API between rate-limit-heavy groups. Do not reset databases, accounts or volumes.

## Live speech and backend compatibility

The live browser check recorded a controlled French WAV through Chromium MediaRecorder, submitted it through the existing multipart API, and received genuine Base/Ollama/Piper results. A private 112,172-byte WAV played via the explicit UI button, with autoplay false and all microphone tracks ended. Conversation text persisted after refresh. See [live speech evidence](FRONTEND_REDESIGN_LIVE_SPEECH.json).

The recognizer still made word errors and the model reply was not a certified pedagogical evaluation. Those outputs were kept as received, not silently replaced by an expected sentence. This check used fake audio input, not a physical microphone or a new ASR accuracy benchmark.

Read-only fingerprints covered all **52 application tables** in main and preview before/after deployment, including existing speech history. No row counts changed. Preview fingerprints matched; main differed only in user-session metadata. No profile, progress, curriculum, AI or speech-history contents changed. See [preservation evidence](FRONTEND_REDESIGN_PRESERVATION.json). No migration or backend container replacement was required; both databases remain at `20261102_0007`.

## Screenshots and local review

- [Desktop Home](frontend-redesign/home-1440.png)
- [Mobile Home](frontend-redesign/home-390.png)
- [Small-screen speaking control](frontend-redesign/speak-320.png)
- [Uncertain transcript review](frontend-redesign/transcript-review.png)
- [Tutor conversation](frontend-redesign/tutor-chat.png)
- [Genuine speech conversation](frontend-redesign/speak-live.png)

Main uses `http://localhost:3000`; developer preview uses `http://localhost:3001`. Inspect `/dashboard`, `/courses`, `/ai-tutor`, `/voice-practice`, `/voice-practice/pronunciation`, `/voice-practice/history`, `/profile` and `/settings`. Public landing, registration, login and protected redirects are additionally browser-checked on both deployed origins; see [deployed browser checks](FRONTEND_REDESIGN_DEPLOYED.json). Authenticated workflow tests use the isolated database, avoiding changes to existing learners' accounts. All six services in each deployed stack are healthy.

## Remaining limitations

Physical microphone checks, additional browser engines and real mobile hardware remain manual. Existing content-publication gates and unavailable acoustic pronunciation scoring are unchanged. ASR and generated tutor replies can still be inaccurate. Long conversations remain scrollable, with full history in existing routes. No subscriptions, payments, extra learning features or Milestone 07 work were added.
