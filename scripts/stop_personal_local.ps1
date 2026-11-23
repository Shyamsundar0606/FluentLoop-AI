param()
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv312\Scripts\python.exe'
& $python -B (Join-Path $PSScriptRoot 'personal_local.py') stop
if ($LASTEXITCODE -ne 0) { throw 'Graceful shutdown could not be confirmed; dependent databases were not force-stopped.' }
