$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

if (-not (Test-Path ".\.env")) {
    throw ".env was not found. Run: Copy-Item .env.phpstudy.example .env, then update database password and API_TOKEN."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw ".venv was not found. Run: .\scripts\phpstudy\install.ps1 first."
}

$TmpDir = Join-Path $ProjectRoot ".tmp"
if (-not (Test-Path $TmpDir)) {
    New-Item -ItemType Directory -Path $TmpDir | Out-Null
}

$PidFile = Join-Path $TmpDir "phpstudy-uvicorn.pid"
if (Test-Path $PidFile) {
    $ExistingPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ExistingPid) {
        $ExistingProcess = Get-Process -Id ([int]$ExistingPid) -ErrorAction SilentlyContinue
        if ($ExistingProcess) {
            Write-Host "Uvicorn is already running, PID: $ExistingPid"
            exit 0
        }
    }
}

Write-Host "Starting FastAPI service: http://127.0.0.1:8000"
$Process = Start-Process `
    -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $PidFile -Value $Process.Id -Encoding ASCII
Write-Host "Started, PID: $($Process.Id)"
