# Milestone 08.3 verification

Local verification on 7 November 2026. The supplement adds 13 teaching
packets, 12 short A1 draft lessons and 25 exercises. It reuses the existing
être lesson and its six formats. The original A1 content source remains at
`1.0.2`; the independent draft supplement is `0.1.0`.

- [A1 inventory, grammar and vocabulary review](../content/A1_GRAMMAR_CONTENT_REVIEW.md)
- [A1 exercise quality report](../content/A1_EXERCISE_QUALITY_REPORT.md)
- [A1–C2 blueprint](../content/FRENCH_CURRICULUM_BLUEPRINT.md)

Grammar shows topic explanations, contextual vocabulary, examples, common
mistakes and present-tense tables where relevant. Topic practice uses the
existing session engine and returns to the selected topic after completion.
The existing recommendation flow consumes the recorded errors and explicit
objective links. Practice and lesson completion remain separate.

## Database and publication checks

The new importer uses Alembic revision `20261104_0009`. On a disposable
PostgreSQL database it installed the canonical source, the existing six-format
fixture and the supplement. Repeating the canonical import reported zero
inserts, updates or deletes. The supplement reported 13 topics, 12 lessons
and 25 exercises. Repeating it returned the same digest and `unchanged: true`.
The release records five pending review areas and all added content as draft.

Read-only fingerprints matched the Milestone 08.2 baseline across 59 tables
in each of the main and older preview databases. The older preview database
service was temporarily started for inspection and returned to its stopped
state. All 18 captured table fingerprints in the existing M08 demo matched
the pre-work baseline, including the 29 sessions, 136 frozen exercises,
97 attempts and two lesson progress rows. The private baseline also contains
the original IDs and content versions.

The initial import and browser checks used a disposable database. After
explicit approval, the release was applied to the existing isolated demo
database `fluentloop_m08_local_*` at revision `20261104_0009`.
Before applying it, the 18-table baseline matched and a 328,950-byte custom
PostgreSQL backup was restored into a dedicated recovery database. All 59
restored table fingerprints matched the source snapshot. The archive and
restore record are in the ignored private backup area.

The live import and repeat returned the verified release digest and the
expected 13 topics, 12 lessons and 25 exercises. The repeat reported
`unchanged: true`. The imported explanations, bilingual examples,
exercise definitions, objective links and answer keys matched the source.
All five review areas are pending and the demo has zero published lessons.
The original lesson, exercise and option rows matched the restored backup
exactly. The isolated API was restarted. The frontend and speech worker
kept their original listener processes.

Both Playwright cases passed again on the existing demo using the designated
admin and learner. The admin completed a new lesson and focused practice,
reloaded the saved result and returned to the selected topic. The learner
received HTTP 404 for the draft lesson. A separate authenticated read of a
pre-existing completed session returned all six exercise formats with saved
answers, and its listening endpoint returned WAV audio. After the browser
run, all pre-existing rows in 12 curriculum, history and review tables
still matched the restored backup. The browser run added verification
activity and updated sign-in timestamps.

## Verification commands

From the project root in Windows PowerShell, with local PostgreSQL, Redis
and the existing speech worker available:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
Push-Location backend
..\.venv312\Scripts\python.exe -m app.content_import --validate-only
..\.venv312\Scripts\python.exe -m app.grammar_content
..\.venv-speech\Scripts\python.exe -m pytest -o addopts= tests/test_grammar_content.py tests/test_authorized_preview.py tests/test_learning_experience.py -q
Pop-Location
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py tests
.\.venv312\Scripts\python.exe -u backend\scripts\m083_local.py
Push-Location frontend
npm run lint
npm run typecheck
Pop-Location
docker compose ps
```

The existing backend suite reported **251 passed** with two dependency
deprecation warnings. The final focused backend run reported **21 passed**,
including a disposable PostgreSQL import that preserved six frozen exercise
snapshots, all existing lesson versions and all existing option answer keys.
The final Playwright run reported **2 passed**. It
covered the authorized draft banner, guided reading, listening playback and
replay, one simulated audio outage with a successful live retry, grading,
mistakes, persistence after refresh, and return to the selected grammar topic.
It also exercised the tutor and speaking links, keyboard activation of the
practice button, 320 px and 390 px layouts, and learner denial through the
API and direct browser URL. ESLint, TypeScript, the production build and both
source validators passed.

The existing Docker stack reported six healthy services. A live worker
request returned a 22,050 Hz Piper WAV of 1.78 seconds for the coffee request.
Faster-Whisper Base transcribed the existing synthetic French sample and
recognized its expected phrase. Ollama `llama3.2:3b` completed a live request
with nonempty output.

The disposable browser runner builds the frontend, creates a fresh
`fluentloop_m08_3_test_*` database, applies the existing migrations, checks
both imports, and runs Playwright against loopback ports 3012 and 8012.
It stops its two local app processes afterward. Test databases remain
available for inspection. Credentials stay in the test process environment.
Logs and Playwright failure context are written under the ignored private
runtime folder. The runner needs a locally installed Playwright Chromium.

The focused PostgreSQL history check uses the same disposable database
fixture as the existing M08 PostgreSQL tests. Run it from the project root:

```powershell
$runner = @'
import os, subprocess, sys
sys.path.insert(0, 'backend/scripts')
from m08_local import base, env, ROOT
admin = base.set(database='postgres').render_as_string(hide_password=False)
settings = {**os.environ, **env, 'DATABASE_URL': admin,
            'M08_TEST_ADMIN_DATABASE_URL': admin, 'PYTHONPATH': str(ROOT/'backend')}
tests = ['test_grammar_content.py', 'test_grammar_postgres.py',
         'test_authorized_preview.py', 'test_learning_experience.py']
sys.exit(subprocess.call([sys.executable, '-m', 'pytest', '-o', 'addopts=', '-q',
                          *['tests/' + test for test in tests]],
                         env=settings, cwd=ROOT/'backend'))
'@
$runner | .\.venv-speech\Scripts\python.exe -
```

## Manual demo

The draft release is available at `http://127.0.0.1:3008`. The PowerShell
commands below document the approved import and API restart for this run:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\m08_local.py import-grammar
if ($LASTEXITCODE -ne 0) { throw 'The isolated grammar import failed.' }
$listener = Get-NetTCPConnection -LocalPort 8008 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($listener) {
    $previewApi = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    if ($previewApi.CommandLine -notmatch 'm08_local\.py"?\s+api(?:\s|$)') {
        throw 'Port 8008 is occupied by a different process.'
    }
    Stop-Process -Id $listener.OwningProcess
}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_m08_preview.ps1
```

1. Follow the [existing preview sign-in guide](M08_PREVIEW_AUTH_CORRECTION.md#chrome-incognito-retest)
   and confirm **Authorized draft preview**.
2. In Lessons, open **Give and ask for a name**. Read the explanation and
   examples, then try all three exercises. Play the listening audio twice.
3. In Grammar, select the introductions topic and use **Practice this
   grammar**. Complete the set and return using **Back to grammar topic**.
4. Use an incorrect answer to verify the **Review mistakes** link. Refresh
   the results to confirm the saved attempt. Check the tutor and speaking
   buttons on the grammar topic.
5. Use a separate learner session to confirm **Published content only**
   and denial of the new draft lesson URL.

The linguistic, phonetic, pedagogical, answer-key and licensing reviews are
pending. The source authors' CEFR classification is provisional. Automated
speech checks establish that the configured services produce and process
audio. Qualified listening review remains pending.
