# Milestone 03 Verification

**Status:** Implemented and verified. A1 lessons remain unpublished pending independent French-language, pedagogy, answer-key, and licensing review. Milestone 04 has not started.

## Database and content

- Main database remains at Alembic revision `20261101_0003`; all six CEFR levels are present. No migration was run during this publication-preparation pass.
- Main-database user count remains 2. Existing users and account data were preserved.
- Imported A1 source version `1.0.1`, SHA-256 `8c8fb60c5bbfc25a2dca0acbbcae9c540e20330582c66438c5c25eb8519ef53c`.
- PostgreSQL contains 6 courses, 20 units, 10 A1 lessons (all draft), 78 lexeme rows representing 83 source vocabulary entries, 50 exercises, and 0 published lessons. Five additional course outlines are planned for A2-C2.
- The initial `1.0.1` import reported 952 inserts, 127 updates, and 857 unchanged rows. A direct source/database audit then found one obsolete lesson-4 grammar example carried forward from version `1.0.0`. The importer was fixed to reconcile obsolete examples only for source-managed grammar rules, preserving the union of examples still in the current source. Reapplying `1.0.1` reported 0 inserts, 2 updates, 1 scoped deletion, and 1,933 unchanged rows. The stale example is gone; the corrected rule now matches the source.
- Version `1.0.1` provenance records are marked `automated_checked`; none claim independent human review. Source metadata identifies the curriculum as an AI-assisted draft and asserts no publication license.
- No publication operation was run. Draft lessons remain inaccessible to authenticated learner APIs; regression tests verify the A1 course list is empty and direct draft lesson/course details return 404. An unauthenticated request to the course endpoint returns 401 as designed.

## Content audit

- Strict schema validation passed: 10 lessons, 83 vocabulary entries, 50 exercises, five planned outlines, and zero published lessons.
- Duplicate check: 83 vocabulary occurrences resolve to 78 normalized identities, with five repeated occurrences and no conflicting translation or French-definition values. Exercise prompts and example sentences are unique.
- Source-to-PostgreSQL checks cover vocabulary links, French definitions, English translations, grammatical gender, IPA references, examples, grammar rules and examples, dialogue turns, exercise prompts/options/keys, and accepted answers. All 50 database answer keys were checked directly, independently of learner-facing APIs; the correct-option positions are balanced 17/17/16.
- The source contains 36 dialogue turns. The database has 42 present-indicative conjugation records; automated tests verify the seven included paradigms. Pronunciation data includes six phoneme records and one IPA pronunciation record; no media assets are present.
- The lesson-by-lesson review and complete answer-key summary are in [A1_CURRICULUM_REVIEW.md](../content/reviews/A1_CURRICULUM_REVIEW.md). The review is AI-assisted, not independent human approval.

## Automated checks

- Backend: **34 passed**, 2 existing dependency deprecation warnings.
- Content schema validation: **valid**; 10 lessons, 83 vocabulary entries, 50 exercises, five planned outlines, 0 published.
- Frontend lint, TypeScript check, and production build: passed.
- Browser: **2 Playwright tests passed** using the isolated `fluentloop_e2e` database and dedicated Redis at API port 8001. The flow covered rate-limit messaging, registration, email verification, login, onboarding, dashboard level selection, browsing, settings, and sign-out.

## Runtime verification

- Rebuilt and recreated the backend and frontend. Docker Compose waited for backend health before starting the frontend; both services became healthy.
- From the Windows host, `http://localhost:8000/api/v1/health/live`, `/api/v1/health/ready`, `/docs`, and `http://localhost:3000` returned HTTP 200.
- Readiness returned `database.status=connected` and `redis.status=connected`.
- The host frontend and backend were verified after deployment. Browser E2E used the isolated test API, database, and Redis rather than the main accounts or rate-limit state.

## Publication readiness

- **Publication-ready:** none.
- **AI-pass corrections applied; independent review still required:** A1-001 and A1-003 through A1-010.
- **No specific correction identified by this AI pass; independent review still required:** A1-002.
- **Blocked:** all ten lessons pending independent French-language, pedagogy/sequence, and answer-key approval, plus independent licensing/attribution review for the source.

Keep the review template pending. Do not publish content or begin Milestone 04 until the required independent review and license decision are recorded.
