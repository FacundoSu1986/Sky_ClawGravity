# setup_env.ps1 — One-click dev environment setup for Sky-Claw using uv
# Usage: pwsh -ExecutionPolicy Bypass -File scripts\setup_env.ps1
#
# What this does:
#   1. Installs uv (if not already present) via the official installer
#   2. Creates an isolated .venv in the project root
#   3. Syncs all runtime + dev dependencies from uv.lock (reproducible)
#
# Requirements: PowerShell 5.1+ or pwsh (PowerShell 7+), internet access for first run.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==> Sky-Claw environment setup" -ForegroundColor Cyan
Write-Host "    Project root: $ProjectRoot"

# ── 1. Install uv if missing ──────────────────────────────────────────────────
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "`n[1/3] Installing uv..." -ForegroundColor Yellow
    # Official installer — see https://docs.astral.sh/uv/getting-started/installation/
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    # Reload PATH so the new uv binary is visible in the current session
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + $env:PATH
} else {
    $uvVersion = uv --version
    Write-Host "`n[1/3] uv already installed ($uvVersion) — skipping." -ForegroundColor Green
}

# ── 2. Create virtual environment ────────────────────────────────────────────
Write-Host "`n[2/3] Creating virtual environment at .venv..." -ForegroundColor Yellow
Set-Location $ProjectRoot
# uv venv respects the requires-python field in pyproject.toml automatically
uv venv --seed

# ── 3. Sync all dependencies (runtime + dev group) ───────────────────────────
Write-Host "`n[3/3] Syncing dependencies from uv.lock (including dev extras)..." -ForegroundColor Yellow
# --frozen: use the existing lock file exactly — no implicit upgrades
# --extra dev: include the [project.optional-dependencies].dev group
uv sync --frozen --extra dev

Write-Host "`n[OK] Environment ready." -ForegroundColor Green
Write-Host "     Activate with:  .venv\Scripts\Activate.ps1"
Write-Host "     Run tests with:  uv run pytest"
Write-Host "     Lint with:       uv run ruff check ."
