#Requires -Version 5.1
<#
.SYNOPSIS
    Gemini Validate - Anti-hallucination barrier for post-Gemini code review.

.DESCRIPTION
    Run this after Gemini writes code in the Antigravity IDE panel.
    Validates: ruff check -> ruff format -> mypy -> pytest -x --tb=short

.PARAMETER FilePath
    Path to the Python file that Gemini wrote/modified.

.PARAMETER SkipTests
    Skip the pytest step.

.EXAMPLE
    .\scripts\gemini-validate.ps1 -FilePath sky_claw\security\path_validator.py
    .\scripts\gemini-validate.ps1 -FilePath sky_claw\core\schemas.py -SkipTests
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$FilePath,

    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$python = ".venv\Scripts\python.exe"

# Verify venv exists
if (-not (Test-Path $python)) {
    Write-Host "[FAIL] Virtual environment not found at $python" -ForegroundColor Red
    Write-Host "       Run: uv sync" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[SHIELD] Gemini Anti-Hallucination Validator" -ForegroundColor Cyan
Write-Host "         Target: $FilePath" -ForegroundColor Gray
Write-Host ""

$allPassed = $true

# -- Step 1: ruff check --
Write-Host "  [1/4] ruff check..." -ForegroundColor Yellow -NoNewline
$ruffResult = & $python -m ruff check --fix $FilePath 2>&1
$ruffExit = $LASTEXITCODE

if ($ruffExit -ne 0) {
    Write-Host " [WARN] issues found (auto-fixed)" -ForegroundColor Yellow
    Write-Host $ruffResult -ForegroundColor DarkGray
} else {
    Write-Host " [OK] clean" -ForegroundColor Green
}

# -- Step 2: ruff format --
Write-Host "  [2/4] ruff format..." -ForegroundColor Yellow -NoNewline
& $python -m ruff format $FilePath 2>&1 | Out-Null
$fmtExit = $LASTEXITCODE

if ($fmtExit -ne 0) {
    Write-Host " [FAIL] format failed" -ForegroundColor Red
    $allPassed = $false
} else {
    Write-Host " [OK] formatted" -ForegroundColor Green
}

# -- Step 3: mypy --
Write-Host "  [3/4] mypy type-check..." -ForegroundColor Yellow -NoNewline
$mypyResult = & $python -m mypy $FilePath --config-file=pyproject.toml 2>&1
$mypyExit = $LASTEXITCODE

if ($mypyExit -ne 0) {
    Write-Host " [FAIL] type errors" -ForegroundColor Red
    Write-Host $mypyResult -ForegroundColor DarkRed
    $allPassed = $false
} else {
    Write-Host " [OK] types clean" -ForegroundColor Green
}

# -- Step 4: pytest --
if (-not $SkipTests) {
    Write-Host "  [4/4] pytest -x --tb=short..." -ForegroundColor Yellow -NoNewline
    $testResult = & $python -m pytest -x --tb=short 2>&1
    $testExit = $LASTEXITCODE

    if ($testExit -ne 0) {
        Write-Host " [FAIL] tests failed" -ForegroundColor Red
        $testResult | Select-Object -Last 30 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor DarkRed
        }
        $allPassed = $false
    } else {
        Write-Host " [OK] all passed" -ForegroundColor Green
    }
} else {
    Write-Host "  [4/4] pytest... SKIP" -ForegroundColor Gray
}

# -- Summary --
Write-Host ""
if ($allPassed) {
    Write-Host "[PASS] All validations passed! Code is ready for review." -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] Validation FAILED. Gemini may have hallucinated. Review the errors above." -ForegroundColor Red
    exit 1
}
