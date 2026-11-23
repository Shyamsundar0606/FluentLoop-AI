param()
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv312\Scripts\python.exe'
& $python -B (Join-Path $PSScriptRoot 'personal_local.py') reconcile-stopped --confirm-stopped-review --config (Join-Path $PSScriptRoot '..\.publication-private\personal-local\config.json')
if ($LASTEXITCODE -ne 0) { throw 'Stopped-state review refused. No process, service or protected data was changed.' }
