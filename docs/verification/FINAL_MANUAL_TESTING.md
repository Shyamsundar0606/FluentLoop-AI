# Final consolidated acceptance procedure

**Current gate:** do not run the WSL startup commands or request owner acceptance
until the [documented infrastructure recovery](RELEASE_CANDIDATE_CHECKLIST.md)
is authorized and completed. The RC session's isolated Docker image pull exhausted
C: and Ubuntu is emergency read-only. Manual acceptance remains deferred.

Updated 2026-11-15. Run this single session after the remaining implementation and
security gates are complete. No intermediate owner testing is requested.
The older checkpoint procedures below are retained as historical notes and are
superseded by this section and the linked current startup instructions.

Use the guarded service startup and secure temporary credential commands in
[CURRENT_DEVELOPMENT_CHECKPOINT.md](CURRENT_DEVELOPMENT_CHECKPOINT.md).
The verified local demo login is `http://127.0.0.1:3012/login` while the runner is
active. The default build works; `--webpack` is an explicitly available alternative.
Keep the temporary password, email tokens, raw audio and private responses out of
reports. Record browser/OS, device, viewport, date, expected/actual result and issue
reference for every failed step. Mark unimplemented controls pending rather than pass.

1. In a fresh disposable mail-enabled acceptance environment, register, receive
   verification email, verify, log in, reset a password, complete onboarding and
   select a CEFR level. The current seeded demo verifies login/onboarding but is
   not a replacement for the still-pending live Mailpit registration journey.
2. Check the five navigation destinations: Home, Learn, AI Tutor, Speak, Profile.
   Browse all six CEFR levels without changing the saved account level. Confirm
   honest empty states where published content is unavailable.
3. With the authorized preview account, open grammar explanations, vocabulary,
   conjugation/examples and a draft lesson. Complete choice, fill-blank, ordering,
   matching, listening and short-answer activities. Use the existing French accent
   controls or a configured keyboard. Save, reload and resume; verify feedback and
   final saved answers. Draft labels must remain visible.
4. Complete grammar, vocabulary, reading and listening assessments. Confirm the
   reading passage persists after reload. Submit original writing, request advisory
   feedback and create a revision. Verify the original and history remain intact.
   Check Progress and recommendations after a deliberate mistake.
5. Start a text scenario including café/hotel/housing/telephone. Check level,
   vocabulary hints, correction timing, saved history and completion summary.
   Check unavailable inference/retry behavior without a fabricated response/score.
6. Select the physical microphone. Record fictional French, stop, inspect and edit
   an uncertain transcription, then explicitly confirm/send. Listen to Piper on the
   actual output device. Test denial, cancel, retry and navigation while recording.
   Verify tracks stop and the saved conversation resumes after refresh. Delete an
   owned saved audio item and verify playback becomes unavailable.
7. In a separate disposable published synthetic fixture, complete a genuine
   activity, explicitly update rewards and verify one award on repeated sync,
   calendar streak and achievement history. Preview content deliberately earns no
   XP. Disable motivation in Settings, refresh and confirm the choice persists.
8. Save profile and timezone. Inspect sessions, sign out all devices and verify
   revocation. Read retention information. Confirm your password to download each
   account-data section and any additional pages. Check your own records and absence
   of credentials/curriculum keys; store exported files securely. In a fresh disposable
   account, enter the current password and type `DELETE MY ACCOUNT`; verify permanent
   deletion signs out the account and prevents login. Confirm another account remains
   intact. Inspect the stated audio retry, backup and audit retention exceptions.
   Separately test deactivation, which retains learning data and is not deletion.
9. Switch to the ordinary learner account. Draft courses/grammar/practice/
   assessments, staff authoring, another account's writing and private audio must
   remain unavailable. Use synthetic review/publication records only in disposable
   tests; do not publish the actual draft curriculum during acceptance.
10. Repeat key routes at 320px, 390px, tablet and desktop. Test keyboard-only access,
    skip link, visible focus, labels, error/status announcements, screen reader,
    reduced motion, contrast and meaningful audio alternatives. Record actual human
    outcomes, including any device-dependent speech issue.

Close the demo and its separately started worker with Ctrl+C. Stop only the owned
disposable database services using the guarded helper. Retain the backup/test
cluster for approved cleanup. Public launch and protected migrations remain
separate authorization decisions.

After an abnormal stop, the generated credential file can remain even when the
ports are closed. Remove only `.publication-private/m08/m09-manual-fixture.json`
after confirming the owned demo has stopped. Never copy its contents into reports.

## Historical manual checkpoint notes

Prepared 2026-11-15. These procedures are pending execution. The updated owner
request defers manual acceptance until all technical preparation is complete.
Continue automated implementation checks in the meantime. The audited services
were unavailable except for a listening Ollama port.

## M09 checks within final consolidated acceptance

Use the existing disposable runner only after local PostgreSQL, Redis, Ollama and
the speech worker are available. Inspect service configuration before starting them.
The runner requires its ignored local M08 state and Python/Node dependencies.
It creates a new disposable database, applies migrations there, imports fixtures
there and starts its own API and frontend. Inspect ports 3012 and 8012 first and
resolve conflicts without stopping unrelated services.

Run from the project root in PowerShell.

```powershell
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py --serve-coach
```

Wait for the explicit readiness message. Open `http://127.0.0.1:3012/login` in a
normal browser with the physical microphone selected. In a second terminal copy
one credential at a time and paste it before copying the next.

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m083_local.py --copy-coach-email
.\.venv312\Scripts\python.exe backend\scripts\m083_local.py --copy-coach-password
```

Clear the clipboard after sign-in with `Set-Clipboard -Value ''`. Keep credentials,
raw recordings and private conversation text out of Git and acceptance reports.

1. Open AI Tutor, Conversation practice, Ordering at a boulangerie. Start text
   practice, select easier difficulty and corrections after the conversation.
2. Send an original French response. Ask for a brief explanation. Finish, reopen
   History and confirm saved messages and summary after refresh.
3. Start speaking from the scenario card. Grant microphone permission and say
   “Bonjour, je voudrais une baguette, s'il vous plaît.” into the physical device.
4. Stop and send the recording. Inspect the actual transcription. Correct and
   explicitly confirm uncertain text before it is sent to the tutor.
5. Play the tutor audio and confirm audible French output on the intended device.
   Record whether the reply is understandable and whether any transcript errors
   require correction. Avoid turning transcription quality into a pronunciation score.
6. Reload, reopen the shared transcript and verify that saved turns persist.
7. Test denied microphone permission, cancel and retry. Confirm understandable
   recovery messages and that recording ends after stop or navigation.
8. Record date, operator confirmation, browser/version, OS, physical input/output
   devices, result of each step and defect references. Mark incomplete steps pending.

Stop with Ctrl+C in the runner terminal. Its `finally` block terminates its child
API/frontend processes and removes the temporary credential file. Verify ports are
released. The generated test database remains disposable test data subject to an
explicit, correctly targeted cleanup procedure. Never remove protected volumes.

## Later milestone manual acceptance

Some later milestone controls remain unimplemented. Execute each row only after
its implementation and automated verification are ready.

| Area | Required observed evidence |
| --- | --- |
| Assessments | Authorized grammar/vocabulary/reading/listening session, original writing, saved results/history, resume, second-account denial |
| Analytics | Counts reconciled with saved attempts, empty evidence handled, recommendations traceable to actual mistakes |
| Curriculum | Exact-version reviewer evidence, draft denial for ordinary learners, publication tested only with disposable synthetic approvals |
| Motivation | Real completed activity reward, retry without duplicate XP, timezone boundary and disabled preferences |
| Accounts | Registration/verification/reset, export and deletion behavior, retention and isolation |
| Accessibility | Keyboard traversal, visible focus, screen-reader announcements, contrast, audio alternatives, 320px/390px/tablet/desktop layouts |
| Recovery | Disposable backup restored successfully, snapshots and history reconciled, failure handling observed |
| Release | Integrated learner journey, real service checks and all approval gates recorded |

Public launch, actual curriculum publication, persistent migrations, infrastructure
purchases and DNS changes require their separately authorized procedures.

## Current M10 automated checkpoint

The frontend route is `/assessments`, with five-category selection at the saved
level, shared objective session/results, writing practice and saved history.
Progress adds evidence at `/progress`. These require an API with authorized content.
The temporary browser test frontend used port 3017 with mocked API responses only.
It is not a usable learner demo and has no test credential helper.

The existing coach runner remains an M09 demo. The new assessment wrapper below
adds the draft release. Its service preflight was verified, but full startup is
pending PostgreSQL and Redis availability. These are reference commands for the
final consolidated session, not a request to perform manual acceptance now.

## Assessment demo reference commands

Prerequisites include the existing private `.env`, ignored local M08 connection
state, PostgreSQL, Redis, Python/Node dependencies and free ports 3012/8012. Inspect
running services and their target configuration before starting them. The runner
creates a new `fluentloop_m08_3_test_*` database, applies migrations there, imports
drafts there and creates temporary accounts. It never runs migrations on the saved
M08 database URL. The build may be selected explicitly with webpack while the
default Turbopack defect is unresolved.

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py serve --webpack
```

After the readiness message, the login URL is `http://127.0.0.1:3012/login`,
Assessments is `http://127.0.0.1:3012/assessments`, Progress is
`http://127.0.0.1:3012/progress` and the API is `http://127.0.0.1:8012/api/v1`.
These URLs are available only while the demo is running.

Copy each temporary preview-account credential separately and paste before copying
the next. The preview account is an admin identity in this disposable environment.

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py copy-email
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py copy-password
Set-Clipboard -Value ''
```

In final acceptance, complete grammar and listening practice. Complete vocabulary
meaning, French response, matching and contextual questions. Open Lina's reading
passage, answer a question, save and exit, resume and inspect saved results. Submit
three original writing sentences, request optional feedback, refresh the saved URL
and create a revision. Confirm the earlier original response remains in history.
Check Progress and mistake-practice links after deliberately missing a question.

For ordinary-learner denial, sign out and copy the separate learner email, then use
the password helper again. Draft assessments and the preview account's writing
history must be unavailable to this account. All seeded content remains draft.

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py copy-learner-email
.\.venv312\Scripts\python.exe backend\scripts\m10_local.py copy-password
```

If speech is unavailable, inspect the existing speech-worker configuration and
check port 8098 before starting the local worker in a separate terminal with the
existing optional speech environment. Do not replace an unrelated worker.

```powershell
.\.venv-speech\Scripts\python.exe backend\scripts\m08_local.py worker
```

Stop the demo with Ctrl+C in its terminal. Stop any worker started for this session
with Ctrl+C in its separate terminal. The runner removes its credential file and
terminates its own API/frontend children. Disposable databases remain for explicit
targeted cleanup. A complete backup/restore rehearsal and final M12–M17 manual
checklist still need to be added when those phases are implemented.
