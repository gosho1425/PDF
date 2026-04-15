# ─────────────────────────────────────────────────────────────────────────────
# PaperLens – Windows environment diagnostics
# Run from the project root: .\scripts\check-env.ps1
# ─────────────────────────────────────────────────────────────────────────────
$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  PaperLens – Environment Diagnostics (Windows)"    -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── 1. Docker Desktop check ──────────────────────────────────────────────────
Write-Host "1. Docker Desktop" -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "   ✓ $dockerVersion" -ForegroundColor Green

    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ✗ Docker daemon is not running." -ForegroundColor Red
        Write-Host "     → Open Docker Desktop from the Start Menu and wait for it to show 'Running'." -ForegroundColor Gray
    } else {
        Write-Host "   ✓ Docker daemon is running." -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ Docker not found. Install from https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
}

Write-Host ""

# ── 2. .env file check ───────────────────────────────────────────────────────
Write-Host "2. .env file" -ForegroundColor Yellow
if (-not (Test-Path $EnvFile)) {
    Write-Host "   ✗ .env file is MISSING." -ForegroundColor Red
    Write-Host "     → Run: Copy-Item .env.example .env" -ForegroundColor Gray
    Write-Host "     → Then edit .env and fill in POSTGRES_PASSWORD and ANTHROPIC_API_KEY" -ForegroundColor Gray
    exit 1
} else {
    Write-Host "   ✓ .env file exists." -ForegroundColor Green
}

Write-Host ""

# ── 3. Parse .env values ─────────────────────────────────────────────────────
$envVars = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Length -eq 2) {
            $envVars[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

# ── 4. POSTGRES_PASSWORD check ───────────────────────────────────────────────
Write-Host "3. POSTGRES_PASSWORD" -ForegroundColor Yellow
$pgPass = $envVars["POSTGRES_PASSWORD"]
if ([string]::IsNullOrWhiteSpace($pgPass) -or $pgPass -match "CHANGE_ME") {
    Write-Host "   ✗ POSTGRES_PASSWORD is empty or still the placeholder value." -ForegroundColor Red
    Write-Host "     → Open .env and change POSTGRES_PASSWORD to a real password (no spaces)." -ForegroundColor Gray
    Write-Host "     → Example: POSTGRES_PASSWORD=PaperLens2024!" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   ⚠  This is the most common reason pdf-db-1 fails to start." -ForegroundColor Yellow
} else {
    Write-Host "   ✓ POSTGRES_PASSWORD is set (length: $($pgPass.Length) chars)." -ForegroundColor Green
}

Write-Host ""

# ── 5. ANTHROPIC_API_KEY check ───────────────────────────────────────────────
Write-Host "4. ANTHROPIC_API_KEY" -ForegroundColor Yellow
$apiKey = $envVars["ANTHROPIC_API_KEY"]
if ([string]::IsNullOrWhiteSpace($apiKey) -or $apiKey -match "XXXX") {
    Write-Host "   ✗ ANTHROPIC_API_KEY is empty or still the placeholder value." -ForegroundColor Red
    Write-Host "     → Get your key from https://console.anthropic.com/ (starts with sk-ant-)" -ForegroundColor Gray
    Write-Host "     → The app starts without it, but PDF extraction will fail." -ForegroundColor Gray
} else {
    Write-Host "   ✓ ANTHROPIC_API_KEY is set (starts with: $($apiKey.Substring(0, [Math]::Min(10, $apiKey.Length)))...)" -ForegroundColor Green
}

Write-Host ""

# ── 6. HOST_PAPER_DIR check ──────────────────────────────────────────────────
Write-Host "5. HOST_PAPER_DIR (PDF ingestion folder)" -ForegroundColor Yellow
$paperDir = $envVars["HOST_PAPER_DIR"]
if ([string]::IsNullOrWhiteSpace($paperDir)) {
    Write-Host "   ⚠  HOST_PAPER_DIR is not set." -ForegroundColor Yellow
    Write-Host "     → The fallback ./data/ingest will be used (empty folder)." -ForegroundColor Gray
    Write-Host "     → Set HOST_PAPER_DIR=C:\path\to\your\pdfs in .env to ingest real files." -ForegroundColor Gray
} elseif (-not (Test-Path $paperDir)) {
    Write-Host "   ✗ HOST_PAPER_DIR='$paperDir' does not exist on this machine." -ForegroundColor Red
    Write-Host "     → Create the folder or update HOST_PAPER_DIR in .env." -ForegroundColor Gray
} else {
    $pdfCount = (Get-ChildItem -Path $paperDir -Recurse -Filter "*.pdf" -ErrorAction SilentlyContinue).Count
    Write-Host "   ✓ HOST_PAPER_DIR='$paperDir' exists ($pdfCount PDF file(s) found)." -ForegroundColor Green
}

Write-Host ""

# ── 7. Stale volume warning ───────────────────────────────────────────────────
Write-Host "6. Stale Docker volume check" -ForegroundColor Yellow
$volumeExists = docker volume ls --format "{{.Name}}" 2>&1 | Select-String "pdf_postgres_data"
if ($volumeExists) {
    Write-Host "   ℹ  Volume 'pdf_postgres_data' already exists." -ForegroundColor Cyan
    Write-Host "     → If you changed POSTGRES_PASSWORD after a previous run, you must reset the volume:" -ForegroundColor Gray
    Write-Host "        docker compose down -v   (WARNING: deletes all stored papers and data)" -ForegroundColor Gray
    Write-Host "        docker compose up -d" -ForegroundColor Gray
} else {
    Write-Host "   ✓ No existing volume — fresh start." -ForegroundColor Green
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Diagnostics complete. Fix any ✗ items above,"
Write-Host "  then run: docker compose up -d"
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
