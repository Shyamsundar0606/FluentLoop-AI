param(
    [string]$Config = (Join-Path $PSScriptRoot '..\.publication-private\personal-local\config.json'),
    [switch]$CheckOnly,
    [switch]$ApproveProtectedServices,
    [switch]$RecoveryPrerequisitesSatisfied,
    [switch]$InfrastructureOnly
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv312\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'The existing .venv312 Python is missing; no installation was attempted.' }
$taskArgs = @('-B', (Join-Path $PSScriptRoot 'personal_local.py'), 'start', '--config', $Config)
if ($CheckOnly) { $taskArgs += '--check-only' }
if ($ApproveProtectedServices) { $taskArgs += '--approve-protected-services' }
if ($RecoveryPrerequisitesSatisfied) { $taskArgs += '--recovery-prerequisites-satisfied' }
if ($InfrastructureOnly) { $taskArgs += '--infrastructure-only' }
# Runs in this console; Ctrl+C requests the same graceful shutdown as Stop.
& $python @taskArgs
if ($LASTEXITCODE -ne 0) { throw 'Personal startup stopped. Read the message above; no destructive fallback is used.' }
