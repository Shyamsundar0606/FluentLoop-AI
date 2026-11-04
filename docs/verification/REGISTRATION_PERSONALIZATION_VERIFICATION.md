# Registration and tutor personalization enhancement

Verified 2 November 2026. This is an enhancement to Milestones 01–05, not Milestone 06.

## Result and expected screens

- Registration shows required **Full name**, **Email**, **Password** and existing password confirmation, plus **Age (optional)**. Blank/whitespace names and invalid email/password are rejected. If age is supplied, it must be a whole number from 0 through 120. Age may always be omitted; no new minimum-age or eligibility restriction was introduced, as requested.
- Full name initializes the existing `user_profiles.display_name`; no duplicate legal-name column is added. Single names and international names are supported without requiring a surname or two words. The legacy API `display_name` request field still works. Conflicting old/new name fields are rejected.
- Only `under_18` or `18_or_over`, or NULL when omitted, is retained in `registration_age_band`. This is a snapshot at registration, not a current-age calculation or verified eligibility claim. Exact age, birth date and birth year are not stored. The band is not included in ordinary profile/auth responses or tutor prompts.
- Onboarding greets the learner with the authenticated profile name. It does not ask for the name again or put the name into localStorage onboarding answers.
- Dashboard welcomes the learner by current `display_name` from the existing authenticated `/auth/me` profile projection. It does not load identity from localStorage. The separately saved preferred-name field is preserved; the dashboard now consistently displays the registered/editable display name.
- Profile settings keep the editable **Display name** field. Saving refreshes the authenticated user context, so the dashboard and tutor page reflect the edit, including after refresh.
- Tutor page says “Welcome, [display name]. Ready to practice French?” The backend derives a bounded first-name hint from the currently authenticated profile for every generation. Only that first token is sent in a separate untrusted identity message, separate from curriculum/scenario data and stored turns. Unsupported/suspicious fragments or tokens over 40 characters omit the hint. No email, age, age band, password or session/CSRF token is added from the profile. A name naturally used in a generated greeting remains ordinary saved conversation text.
- Tutor policy allows natural, sparing first-name address and forbids asking for the learner's name again except as a French-language exercise. No user-supplied name/identity field is added to the chat API. Existing CEFR, source authorization, ownership, conversation levels and history remain unchanged.

## Migration

Confirmed deployed head before this change: `20261102_0005` on main and preview. New additive revision **`20261102_0006`** adds only nullable `user_profiles.registration_age_band VARCHAR(16)` and a check constraint for the two permitted values. No existing profile name, account, session, preference, progress, curriculum or AI conversation row is backfilled or overwritten. Existing age bands remain NULL. The revision number is migration sequencing, not the start of Milestone 06.

Upgrade / rollback to 0005 / re-upgrade were executed against the new isolated `fluentloop_m05_personalization` database with a preexisting named profile and imported draft curriculum. Every preexisting table row fingerprint was preserved by that test. Rollback drops only the new band column/constraint and was never run against either application database.

Both application stacks were rebuilt and upgraded to 0006. Database, Redis and Mailpit containers/volumes were retained. The preserved row counts include:

Final runtime recheck after the interrupted turn: Docker Desktop's Linux engine pipe was unavailable, so current service health and a final `alembic current` could not be re-confirmed. Earlier application rebuild/start and migration-preservation checks completed as recorded below. No test listener remained on port 8015 at the final check. Start Docker Desktop before reopening the application stacks.

| Environment | Users | Profiles | Sessions | Lessons | AI conversations/messages | Learning sessions/attempts/progress |
|---|---:|---:|---:|---:|---|---|
| Main | 2 | 2 | 2 | 10 | 1 / 6 | 0 / 0 / 0 |
| Preview | 2 | 2 | 8 | 10 | 0 / 0 | 3 / 11 / 2 |

All 47 application-table row counts were preserved in each database. Existing profile hashes match exactly when excluding the new nullable field. Users, names, progress and existing AI conversation/message content were preserved. Full-table checksums differed for main `user_sessions` during observed authenticated app activity, and preview `lexemes` during its existing startup importer (zero inserts/deletes, two updates). A separate isolated repetition confirmed that importer leaves lexeme content unchanged while update timestamps can change. These operational checksum differences are recorded rather than reported as byte-for-byte preservation. Evidence: [aggregate preservation snapshots](REGISTRATION_PERSONALIZATION_PRESERVATION.json). No profile content or credentials are stored in that evidence file.

## Tests actually run

| Check | Result |
|---|---|
| Complete backend regression | **92 passed, 1 skipped**; the skipped test is the explicitly opt-in PostgreSQL integration test; two existing dependency deprecation warnings |
| New registration/personalization tests plus tutor tests | **56 passed** in the targeted run |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Next.js production build | Passed |
| Full Playwright suite on isolated API/PostgreSQL | **11 passed, 1 skipped**; the optional separately configured M04 live lesson smoke was not enabled in this run |
| Final registration/profile Playwright rerun | **3 passed**, including the final tutor greeting copy |
| Real PostgreSQL registration flow | Passed: isolated registration, local Mailpit verification, login, onboarding, selected-level changes, profile display-name edit, dashboard/tutor refresh and sign-out |
| Opt-in real PostgreSQL tutor regression | **1 passed** separately on the upgraded isolated database: concurrent turns, replay, persistent history and evidence-backed recommendations |
| Persisted registration data inspection | Passed: updated display name, completed onboarding and only `18_or_over` retained; no exact-age or birth-date columns |
| Migration preservation | Passed: isolated populated upgrade / downgrade / re-upgrade |
| Genuine Ollama personalization | Passed with installed `llama3.2:3b`: a response used the supplied first name “Camille”; no profile email/age was supplied |

Backend tests cover optional/absent and boundary ages, rejecting negative/over-range/fractional/string/bool ages, full-name normalization, invalid required fields, legacy request compatibility, automatic profile creation, duplicate-registration name preservation, CSRF, owner isolation, unchanged onboarding names, updated-name prompt freshness, international/bounded first-name extraction and no synthesized identity turns persisted. Tests capture exact provider messages to verify exclusion of surname, email, age band and authentication data. Existing authentication, curriculum, learning and tutor tests also pass.

The complete browser flow creates disposable accounts only in `fluentloop_m05_personalization`, with fake model inference. Genuine Ollama personalization was tested separately and is not inferred from browser mocks. Generation remains probabilistic; the prompt policy is not a guarantee of linguistic accuracy or perfect instruction adherence.

## Files changed

Backend:

- `backend/app/schemas.py` — full-name alias compatibility and optional strict age validation.
- `backend/app/models.py` — nullable minimized age band and database constraint.
- `backend/app/api/v1/auth.py` — automatic profile creation stores name and derived band only.
- `backend/app/ai/prompts.py` — minimal name extraction, separate identity context and name-aware policy.
- `backend/app/ai/orchestrator.py` — current authenticated profile hint and identity-context echo rejection.
- `backend/alembic/versions/20261102_0006_profile_registration_age_band.py` — additive migration.
- `backend/tests/test_registration_personalization.py` — registration, preservation, profile and prompt-privacy tests.
- `backend/scripts/verify_profile_migration.py` — read-only snapshots and isolated-only rollback verification.

Frontend:

- `frontend/app/register/page.tsx` — full name, optional age, field validation and privacy explanation.
- `frontend/app/onboarding/page.tsx` — registered-name greeting.
- `frontend/app/dashboard/page.tsx` — authenticated display-name welcome.
- `frontend/app/profile/page.tsx` — display-name validation and explanation.
- `frontend/app/ai-tutor/page.tsx` — current-profile welcome.
- `frontend/e2e/auth-flow.spec.ts` — age/name validation, complete registration and refreshed name assertions.

Documentation: README, `docs/ai/tutor-prompt-design.md`, this report and the aggregate preservation JSON. No runtime dependencies, authentication protections, rate limits, publication rules or existing data were removed.

## Verification commands

From the project root, use the installed Python environment and npm.cmd in PowerShell:

```powershell
Push-Location backend
..\.venv312\Scripts\python.exe -m pytest tests -ra
Pop-Location
Push-Location frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
Pop-Location
```

For isolated browser checks, use the guarded `scripts.ai_e2e_server` setup in [Ollama setup](../ai/ollama-setup.md), replacing the database name with `fluentloop_m05_personalization`, and run:

```powershell
Push-Location frontend
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3015'
$env:PLAYWRIGHT_API_BASE_URL = 'http://127.0.0.1:8015/api/v1'
$env:AI_E2E_REAL_API = '1'
npm.cmd exec -- playwright test --workers=1
Pop-Location
```

Never run the disposable registration tests against main or preview. The snapshot script is read-only by default; its `rollback-test` mode refuses any database other than `fluentloop_m05_personalization`.
