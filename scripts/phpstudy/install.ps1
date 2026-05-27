$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "python was not found. Install Python 3.12 and make sure python is in PATH."
}

$VersionOutput = & python --version
Write-Host "Current Python: $VersionOutput"
if ($VersionOutput -notmatch "Python 3\.12") {
    Write-Warning "Python 3.12 is recommended. The current version may work, but it is not the verified baseline."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment .venv ..."
    & python -m venv .venv
}

Write-Host "Upgrading pip ..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip

Write-Host "Installing project dependencies ..."
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Write-Host "Dependency installation completed."
