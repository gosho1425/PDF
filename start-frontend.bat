@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  PaperLens — Start Frontend (Next.js)
REM  Run start-backend.bat FIRST, then run this in a separate window.
REM ─────────────────────────────────────────────────────────────────────────────
title PaperLens Frontend

cd /d "%~dp0frontend"

REM ── Check Node.js ────────────────────────────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Node.js not found.
    echo  Download and install it from: https://nodejs.org/  (LTS version)
    pause
    exit /b 1
)

REM ── Install dependencies ─────────────────────────────────────────────────────
if not exist "node_modules" (
    echo.
    echo  Installing Node.js dependencies (first run only, may take a minute)...
    npm install
    if errorlevel 1 (
        echo  [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

REM ── Start Next.js dev server ─────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║  PaperLens Frontend starting...                                      ║
echo  ║  Open your browser at: http://localhost:3000                         ║
echo  ║  Press Ctrl+C to stop.                                               ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.

npm run dev
