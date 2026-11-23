# Historical admin-fixture browser setup

The old tests shared the `M08_E2E_REAL_API` flag with newer personal-preview tests,
but silently read an older fixture from `.speech-data`. Running them against a
learner-only API could not authenticate their expected admin account. Failed
attempts also consumed that disposable API's rate-limit budget. Main permissions
and application authentication were not the cause.

`scripts/admin_browser_harness.py prepare` now creates a fresh localhost-only
`fluentloop_browser_admin_*` database, migrates only that database, seeds the
original course/interactive 0.1.1 fixture and creates two synthetic test accounts.
It verifies storage, unused ports 8002/3002 and an empty Redis DB15. It never flushes
Redis, starts infrastructure, changes protected accounts or replaces old fixture
files. Credentials and state stay under ignored `.publication-private`.

The script prints a state-file path. Run `serve STATE_FILE` in a retained console.
Configure Playwright with API `http://127.0.0.1:8002/api/v1`, frontend
`http://127.0.0.1:3002`, `M08_E2E_REAL_API=1`,
`M08_E2E_SESSION_COOKIE_NAME=fluentloop_admin_test_session` and
`PLAYWRIGHT_ADMIN_FIXTURE` pointing to the sibling `fixture.json`.
Run `authorized-preview.spec.ts` and `learning-experience.spec.ts` with one worker.
The seven original assertions remain intact. Signal graceful API shutdown by
creating the sibling `stop` file. No database or cache cleanup is automatic.

On 22 November 2026 all seven tests passed in 40.0 seconds in the dedicated stack.
Evidence: `.publication-private/admin-browser-20261122-213123-34415f/browser.log`.
Preparation also exposed and fixed two harness assumptions: migrations already
seed CEFR rows, and the interactive importer does not return a `reused` flag.
A first account fixture used `.test` domains rejected by the API's email validator;
the harness now validates synthetic `example.com` addresses before insertion.
Earlier failed disposable attempts and logs were preserved. Test assertions,
rate limits, cookie checks and draft authorization rules were not weakened.
