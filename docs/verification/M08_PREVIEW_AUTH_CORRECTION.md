# M08 developer-preview authentication

Verified locally on 7 November 2026, Europe/Paris. The preview frontend is
`http://127.0.0.1:3008` and its API is `http://127.0.0.1:8008/api/v1`.

## Diagnosis

The isolated M08 PostgreSQL database recorded 26 recent non-headless Chrome-like
learner sessions. The latest was at 12:57 Paris time on 7 November. The latest
admin sessions that day used headless Chrome or other clients. The latest
non-headless Chrome-like admin session before this investigation was on
5 November. All four Chrome-like non-headless sessions recorded on 7 November
before 13:00 belonged to ordinary learner accounts outside the designated
fixture pair. Two had no recorded revocation. This supports an account
mismatch in the reported manual test.
User-agent metadata cannot identify a particular Incognito window or establish
whether autofill, an existing tab, or the submitted email selected the learner.
The user's Chrome profile and live session were outside the controlled test.

The helper selected the existing active, verified synthetic admin in
`fluentloop_m08_local_*`. Its fixture password validated against the existing
stored hash. The separately designated learner was active and verified with
role `learner`. The launcher reused the existing loopback services. Fixture
preparation reported 46 unchanged items and zero inserts, updates, or deletes.
The isolated database was at revision `20261104_0009` with 11 draft lessons.

The API checks the login origin and rate limit, validates the password and email
verification, and stores a hashed opaque session token. The frontend fetches
`/auth/me` after login and sends credentialed, uncached API requests.
`/learning/access` derives the banner from the authenticated database user.
Draft access requires an active, verified admin and the backend preview setting
in development. The learner banner accurately describes the learner session.
Application authentication and authorization code stayed as it was.

## Cookies and session checks

The isolated M08 origin is allowlisted for credentialed CORS. Both services use
the same host across ports. Cookies are scoped by host and path, so separate
names provide isolation from other local FluentLoop environments.

| Cookie | Host | Path | SameSite | Secure | HttpOnly |
| --- | --- | --- | --- | --- | --- |
| `fluentloop_m08_session` | `127.0.0.1` | `/api/v1` | Lax | No, local HTTP | Yes |
| `fluentloop_m08_csrf` | `127.0.0.1` | `/` | Lax | No, local HTTP | No |

Both cookies are host-only. The frontend reads the CSRF cookie to send
`X-CSRF-Token` on protected mutations. The backend checks the request origin
and token match. Session lookup rejects missing, revoked and expired tokens.
Normal sign-out revokes the current session and clears the two M08 cookies.

## Chrome Incognito retest

Keep the existing main Docker PostgreSQL and Redis running. From PowerShell:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_m08_preview.ps1
```

1. If an M08 tab is already signed in, open **Account options** in the top bar
   and choose **Sign out**. The top-bar menu also works when the Next.js
   development indicator overlaps the sidebar button. Close every Incognito
   window to end the shared Incognito session, then open a new one.
2. Open `http://127.0.0.1:3008/login`. Use the exact IP and port. Replace both
   fields explicitly if Chrome suggests a saved login.
3. Run the email command, paste into Email, then run the password command and
   paste into Password. Clear the clipboard and select **Sign in**.

   ```powershell
   .\.venv312\Scripts\python.exe backend\scripts\m08_local.py copy-email
   .\.venv312\Scripts\python.exe backend\scripts\m08_local.py copy-password
   Set-Clipboard -Value ''
   ```

4. In the same Incognito window, open
   `http://127.0.0.1:8008/api/v1/auth/me` in a separate tab. Privately compare
   the returned email to the helper-selected email and check
   `role: admin` and `email_verified: true`. Open
   `http://127.0.0.1:8008/api/v1/learning/access` and check
   `mode: draft_preview`. Record only the role, verification flag and mode.
   Keep account identifiers, clipboard contents and request headers private.
5. Return to `http://127.0.0.1:3008/courses`. Confirm **Authorized draft
   preview**, refresh, then switch among **Lessons**, **Grammar** and
   **Practice**. Open **Être: understand, practice and remember** in Lessons.
   Start the full lesson or retake a completed one, then advance through the
   reading steps. The exercise sequence is multiple choice, fill in the blank,
   sentence building, word matching, listening and short written response.
   Use **Load French audio** on the listening step.
6. Sign out via **Account options**. Reload the profile API tab and expect
   HTTP 401. To test learner restrictions, use the separate existing M08
   synthetic learner in a fresh context. The profile reports `learner`, the
   access endpoint reports `published_only`, and the draft lesson API returns
   HTTP 404. Use the automated learner test if you do not have that fixture's
   credentials available privately.

If a session appears stale, use the Application panel in Chrome DevTools for
`127.0.0.1` and remove only `fluentloop_m08_session` at `/api/v1` and
`fluentloop_m08_csrf` at `/`. Prefer normal sign-out when available since it
also revokes the server session. Check the launcher output and the exact port
if the profile API returns 401 or the browser calls the wrong API. A 403 on
sign-out calls for checking the origin and matching M08 CSRF configuration.
For HTTP 429, allow the login rate-limit window to expire before retrying.

## Regression commands

```powershell
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3008'
$env:PLAYWRIGHT_API_BASE_URL = 'http://127.0.0.1:8008/api/v1'
$env:PLAYWRIGHT_CSRF_COOKIE_NAME = 'fluentloop_m08_csrf'
$env:M08_E2E_REAL_API = '1'
Push-Location frontend
.\node_modules\.bin\playwright.cmd test authorized-preview.spec.ts --workers=1 --trace off
.\node_modules\.bin\playwright.cmd test authorized-preview.spec.ts learning-experience.spec.ts --headed --workers=1 --trace off
.\node_modules\.bin\playwright.cmd test auth-flow.spec.ts --grep 'registration validates|explain rate limits' --workers=1 --trace off
.\node_modules\.bin\playwright.cmd test auth-flow.spec.ts --grep 'edit profile' --workers=1 --trace off
.\node_modules\.bin\eslint.cmd e2e/authorized-preview.spec.ts
npm run typecheck
Pop-Location
```

The live browser commands can be run independently. Allow the existing
10-attempt, 15-minute login window to expire between repeated live runs if
needed.

The Playwright suite uses a new context per test and the same synthetic
credentials the helper validates. It fills the form explicitly and bypasses
personal browser state and password managers. Tracing is disabled in the
spec to keep login payloads and cookie values out of trace artifacts.

### Browser results

All seven tests in the final headed Chromium run passed on the native M08
frontend and API. The login response and `/auth/me` matched the designated
admin, with `email_verified: true`. The **Authorized draft preview** banner
persisted across refresh and all three Learn tabs. The A1 draft course list
and direct lesson API returned data. Grammar and practice rendered with
authorized content. All six formats were opened and submitted, including
loading French listening audio. Saved answers and progress survived reload
and reauthentication.

The direct draft lesson returned HTTP 404 for the learner, including when
opened by its browser URL. The learner saw **Published content only** and a
foreign default cookie did not grant access. A logout request without the
CSRF header returned 403. The real sign-out cleared both preview cookies,
and `/auth/me` returned 401 even when the revoked cookie was replayed.

Earlier headless Chromium runs also displayed the admin preview banner,
denied the learner, and completed the six-format exercise flow. The final
headed run used a disposable Playwright profile. The personal Chrome
Incognito session and Chrome autofill behavior remain unverified.

### Backend results

Run the focused backend regression tests from the project root. The PostgreSQL
test fixtures create databases with dedicated test prefixes.

```powershell
$runner = @'
import os, subprocess, sys
sys.path.insert(0, 'backend/scripts')
from m08_local import base, ROOT, env
admin_url = base.set(database='postgres').render_as_string(hide_password=False)
settings = {**os.environ, **env, 'DATABASE_URL': admin_url, 'PYTHONPATH': str(ROOT/'backend'),
            'M08_TEST_ADMIN_DATABASE_URL': admin_url, 'STUDY_TEST_ADMIN_DATABASE_URL': admin_url}
names = ['auth', 'authorized_preview', 'curriculum', 'interactive_learning',
         'learning_experience', 'learning', 'study', 'interactive_postgres', 'study_postgres']
sys.exit(subprocess.call([sys.executable, '-m', 'pytest', '-q',
                          *[f'tests/test_{name}.py' for name in names]],
                         cwd=ROOT/'backend', env=settings))
'@
$runner | .\.venv-speech\Scripts\python.exe -
```

The backend command exited successfully. It covered email verification, login
rate limits, expiration and revocation, user ownership, CSRF, content and role
restrictions, and PostgreSQL migration and concurrency behavior. TypeScript
checking and targeted ESLint also passed.

The existing mocked registration and rate-limit UI tests passed. The live
registration-to-sign-out test initially received HTTP 429 on its deliberate
wrong-password attempt because the shared local login limit had been reached.
The retry passed after the window expired. Those two runs added two synthetic
registrations to isolated M08 and their verification messages to local
Mailpit. The focused preview regressions reused the designated fixture
accounts.

### Database preservation

The main and older preview databases were checked by aggregate row
fingerprints. To repeat the historical comparison from the project root:

```powershell
docker compose -p fluentloop-preview -f docker-compose.preview.yml start preview-db
try {
    do {
        docker compose -p fluentloop-preview -f docker-compose.preview.yml exec -T preview-db pg_isready -q
        if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 1 }
    } until ($LASTEXITCODE -eq 0)
    .\.venv312\Scripts\python.exe backend\scripts\m08_local.py preservation
} finally {
    docker compose -p fluentloop-preview -f docker-compose.preview.yml stop preview-db
}
```

The older preview database was stopped at the start of this task. The
preservation check started only its database service, performed read-only
queries and returned it to its original stopped state. Both main and preview
are at revision `20261104_0008`, with ten draft lessons and zero published
lessons each. Before the final headed run, all 59 tables in each database
matched the more recent Milestone 08.2 baseline under
`.publication-private/m08_2/`. A fresh before/after comparison for the
headed run also matched all 59 tables in each database. The earlier M08
baseline predates changes in four older preview tables (`users`,
`user_profiles`, `user_preferences` and `email_verification_tokens`).
Those differences were already present in the first read-only check.

The M08 synthetic account logins and exercises write normal sessions,
attempts and activity to the isolated M08 database. The fixture preparation
reported no content changes. The backend PostgreSQL tests used disposable
databases and the older preview was returned to its stopped state.

## Files changed

- `frontend/e2e/authorized-preview.spec.ts` checks the login response identity,
  current session role, cookie metadata, refresh and tab persistence, direct
  lesson authorization, CSRF and sign-out.
- `docs/verification/MILESTONE_08_1_MANUAL_TESTING.md` points to the current
  identity and effective-access checks.
- This report records the evidence and manual procedure.
