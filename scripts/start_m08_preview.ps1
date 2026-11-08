param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskHelper = Join-Path $taskRoot 'backend\scripts\m08_local.py'
$taskPython = Join-Path $taskRoot '.venv312\Scripts\python.exe'
$taskSpeechPython = Join-Path $taskRoot '.venv-speech\Scripts\python.exe'
$taskLogs = Join-Path $taskRoot '.publication-private\m08_1\runtime'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null

# Reuses the existing verified synthetic admin and the existing isolated DB.
# Refuses production/normal databases; never grants roles, resets DBs or migrates.
& $taskPython $taskHelper prepare-preview
if ($LASTEXITCODE -ne 0) { throw 'Isolated preview preparation failed. No services were started.' }
if ($PrepareOnly) { return }

function Test-TaskListener([int]$Port, [string]$ExpectedCommand) {
    $taskListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $taskListener) { return $false }
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskListener[0].OwningProcess)"
    if ($taskProcess.CommandLine -notmatch $ExpectedCommand) {
        throw "Port $Port is occupied by another process. It was not stopped or modified."
    }
    return $true
}

function Start-TaskPython([string]$Executable, [string]$Action, [int]$Port) {
    if (Test-TaskListener $Port "m08_local\.py.+\b$Action\b") { return }
    Start-Process -FilePath $Executable -ArgumentList @("`"$taskHelper`"", $Action) -WorkingDirectory $taskRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $taskLogs "$Action.out.log") -RedirectStandardError (Join-Path $taskLogs "$Action.err.log") | Out-Null
}

Start-TaskPython $taskPython 'api' 8008
Start-TaskPython $taskSpeechPython 'worker' 8098
if (-not (Test-TaskListener 3008 ([regex]::Escape((Join-Path $taskRoot 'frontend'))))) {
    $taskOldApi = $env:NEXT_PUBLIC_API_BASE_URL
    $taskOldCsrf = $env:NEXT_PUBLIC_CSRF_COOKIE_NAME
    try {
        $env:NEXT_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8008/api/v1'
        $env:NEXT_PUBLIC_CSRF_COOKIE_NAME = 'fluentloop_m08_csrf'
        $taskNode = (Get-Command node.exe).Source
        $taskNext = Join-Path $taskRoot 'frontend\node_modules\next\dist\bin\next'
        Start-Process -FilePath $taskNode -ArgumentList @("`"$taskNext`"", 'dev', '--hostname', '127.0.0.1', '--port', '3008') `
            -WorkingDirectory (Join-Path $taskRoot 'frontend') -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $taskLogs 'frontend.out.log') -RedirectStandardError (Join-Path $taskLogs 'frontend.err.log') | Out-Null
    } finally {
        $env:NEXT_PUBLIC_API_BASE_URL = $taskOldApi
        $env:NEXT_PUBLIC_CSRF_COOKIE_NAME = $taskOldCsrf
    }
}

$taskDeadline = (Get-Date).AddSeconds(45)
do {
    try {
        $taskReady = Invoke-RestMethod 'http://127.0.0.1:8008/api/v1/health/ready' -TimeoutSec 3
        $taskPage = Invoke-WebRequest 'http://127.0.0.1:3008/login' -UseBasicParsing -TimeoutSec 3
        if ($taskReady.status -eq 'ok' -and $taskPage.StatusCode -eq 200) {
            Write-Output 'Local M08 preview ready: http://127.0.0.1:3008/login'
            Write-Output 'Use m08_local.py copy-email and copy-password to paste the existing authorized test credentials without printing them.'
            return
        }
    } catch { }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $taskDeadline)
throw 'The isolated preview did not become ready. Inspect the private runtime logs; main and preview Docker services were not modified.'
