$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PidFile = Join-Path $ProjectRoot ".tmp\phpstudy-uvicorn.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "PID file was not found. The service may not have been started by start.ps1."
    exit 0
}

$PidValue = Get-Content $PidFile -ErrorAction SilentlyContinue
if (-not $PidValue) {
    Remove-Item $PidFile -Force
    Write-Host "PID file was empty and has been removed."
    exit 0
}

$Process = Get-Process -Id ([int]$PidValue) -ErrorAction SilentlyContinue
if ($Process) {
    Write-Host "Stopping FastAPI service, PID: $PidValue"
    Stop-Process -Id ([int]$PidValue) -Force
} else {
    Write-Host "Process was not found. Removing PID file."
}

Remove-Item $PidFile -Force
Write-Host "Stopped."
