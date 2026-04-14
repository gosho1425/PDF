# ─────────────────────────────────────────────────────────────────────────────
# PaperLens — Environment Setup Script for Windows PowerShell
#
# USAGE:
#   Open PowerShell in the project root folder, then run:
#       .\scripts\setup-env.ps1
#
# If you see "cannot be loaded because running scripts is disabled", run this
# first (once, as your user — does NOT require Administrator):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#
# WHAT THIS SCRIPT DOES:
#   1. Checks you are in the right folder (project root)
#   2. If .env does not exist, copies .env.example → .env
#   3. If .env already exists, leaves it untouched
#   4. Prints clear instructions on what to edit next
# ─────────────────────────────────────────────────────────────────────────────

# Pretty output helpers
function Write-Header  { Write-Host "`n$($args[0])" -ForegroundColor Cyan }
function Write-Success { Write-Host "  ✔  $($args[0])" -ForegroundColor Green }
function Write-Warning { Write-Host "  ⚠  $($args[0])" -ForegroundColor Yellow }
function Write-Info    { Write-Host "  →  $($args[0])" -ForegroundColor White }
function Write-Err     { Write-Host "  ✘  $($args[0])" -ForegroundColor Red }

# ── 1. Verify we are in the project root ─────────────────────────────────────

Write-Header "PaperLens — Environment Setup"

$envExample = Join-Path $PSScriptRoot ".." ".env.example"
$envFile    = Join-Path $PSScriptRoot ".." ".env"

# Resolve to absolute paths for clear messages
$envExample = Resolve-Path $envExample -ErrorAction SilentlyContinue
$envFile    = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".." ".env"))

if (-not $envExample) {
    Write-Err "Could not find .env.example in the project root."
    Write-Info "Make sure you are running this script from inside the PDF / paperlens folder."
    Write-Info "Example:"
    Write-Info "  Set-Location C:\Users\YourName\Downloads\PDF-main"
    Write-Info "  .\scripts\setup-env.ps1"
    exit 1
}

Write-Success "Project root found: $(Split-Path $envExample)"

# ── 2. Copy .env.example → .env (if .env does not exist) ─────────────────────

Write-Header "Checking for .env file..."

if (Test-Path $envFile) {
    Write-Warning ".env already exists — leaving it untouched."
    Write-Info    "Location: $envFile"
    Write-Info    "If you want to reset it, delete it and run this script again."
} else {
    Copy-Item $envExample $envFile
    Write-Success ".env created from .env.example"
    Write-Info    "Location: $envFile"
}

# ── 3. Print editing instructions ────────────────────────────────────────────

Write-Header "Next steps — edit your .env file"

Write-Host ""
Write-Host "  Open .env in a text editor and fill in these two required values:" -ForegroundColor White
Write-Host ""

Write-Host "  1. POSTGRES_PASSWORD" -ForegroundColor Yellow
Write-Host "     This is the password for the internal database." -ForegroundColor Gray
Write-Host "     Replace 'CHANGE_ME_STRONG_PASSWORD' with anything strong." -ForegroundColor Gray
Write-Host "     Example:  POSTGRES_PASSWORD=MyPaperLens2024!" -ForegroundColor DarkGray
Write-Host ""

Write-Host "  2. ANTHROPIC_API_KEY" -ForegroundColor Yellow
Write-Host "     This is your Claude AI key from https://console.anthropic.com/" -ForegroundColor Gray
Write-Host "     Replace the placeholder 'sk-ant-XXXX...' with your real key." -ForegroundColor Gray
Write-Host "     Example:  ANTHROPIC_API_KEY=sk-ant-api03-AbCdEfGh..." -ForegroundColor DarkGray
Write-Host ""
Write-Host "     Security note: this key stays on your machine only." -ForegroundColor DarkGray
Write-Host "     It is never sent to the browser or committed to Git." -ForegroundColor DarkGray
Write-Host ""

# ── 4. Offer to open .env in Notepad ─────────────────────────────────────────

Write-Host "  Would you like to open .env in Notepad now? (Y/N) " -ForegroundColor Cyan -NoNewline
$answer = Read-Host
if ($answer -match "^[Yy]") {
    Start-Process notepad.exe $envFile
    Write-Info "Notepad opened. Save the file when done."
} else {
    Write-Info "To open it later:"
    Write-Info "  notepad `"$envFile`""
    Write-Info "  or right-click the file → Open with → your editor"
}

# ── 5. Remind about Docker ────────────────────────────────────────────────────

Write-Header "After editing .env — start the app"

Write-Host ""
Write-Host "  Make sure Docker Desktop is open and running, then:" -ForegroundColor White
Write-Host ""
Write-Host "    docker compose up -d" -ForegroundColor Green
Write-Host ""
Write-Host "  First run downloads images (~5-10 min). Later runs start in seconds." -ForegroundColor Gray
Write-Host ""
Write-Host "  Once running, open your browser:" -ForegroundColor White
Write-Host "    http://localhost:3000   ← Main app" -ForegroundColor Green
Write-Host "    http://localhost:8000/api/docs   ← API docs" -ForegroundColor Green
Write-Host ""
Write-Host "  To stop:  docker compose down" -ForegroundColor DarkGray
Write-Host ""

Write-Success "Setup script complete."
