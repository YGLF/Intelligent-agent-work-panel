$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

if (-not (Test-Path ".\.env")) {
    throw ".env was not found. Run: Copy-Item .env.phpstudy.example .env, then update database password and API_TOKEN."
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw ".venv was not found. Run: .\scripts\phpstudy\install.ps1 first."
}

Write-Host "Ensuring Alembic version table can store long revision ids ..."
& .\.venv\Scripts\python.exe .\scripts\phpstudy\ensure_alembic_version.py
if ($LASTEXITCODE -ne 0) {
    throw "Failed to prepare alembic_version table."
}

Write-Host "Running database migration: alembic upgrade head ..."
& .\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed with exit code $LASTEXITCODE. Do not stamp head until the schema has been manually verified."
}

Write-Host "Database migration completed."
