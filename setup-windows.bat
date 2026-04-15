@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  PaperLens — First-time Windows Setup
REM  Run this ONCE to set everything up, then use start-backend.bat /
REM  start-frontend.bat to launch the app.
REM ─────────────────────────────────────────────────────────────────────────────
title PaperLens Setup
echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║          PaperLens — First-time Windows Setup                        ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.

REM ── Check Python ─────────────────────────────────────────────────────────────
echo  [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Download Python 3.10+ from: https://www.python.org/downloads/
    echo  IMPORTANT: Check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
python --version
echo  [OK] Python found.
echo.

REM ── Check Node.js ─────────────────────────────────────────────────────────────
echo  [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js not found.
    echo  Download Node.js LTS from: https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo  [OK] Node.js found.
echo.

REM ── Backend setup ─────────────────────────────────────────────────────────────
echo  [3/5] Setting up Python backend...
cd /d "%~dp0backend"

python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt

if not exist ".env" (
    copy .env.example .env
    echo.
    echo  ┌─────────────────────────────────────────────────────────────────┐
    echo  │  REQUIRED: Add your Anthropic API key to backend\.env           │
    echo  │                                                                  │
    echo  │  Line to edit:  ANTHROPIC_API_KEY=sk-ant-your-key-here         │
    echo  │                                                                  │
    echo  │  Get a free key: https://console.anthropic.com/                 │
    echo  └─────────────────────────────────────────────────────────────────┘
    echo.
    echo  Opening .env in Notepad... Save and close when done.
    notepad .env
)
echo  [OK] Backend ready.
echo.

REM ── Frontend setup ────────────────────────────────────────────────────────────
echo  [4/5] Installing frontend dependencies...
cd /d "%~dp0frontend"
npm install
echo  [OK] Frontend ready.
echo.

REM ── Done ─────────────────────────────────────────────────────────────────────
echo  [5/5] Setup complete!
echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║  HOW TO START PAPERLENS:                                             ║
echo  ║                                                                      ║
echo  ║  1. Double-click  start-backend.bat   (keep this window open)       ║
echo  ║  2. Double-click  start-frontend.bat  (in a new window)             ║
echo  ║  3. Open browser: http://localhost:3000                              ║
echo  ║                                                                      ║
echo  ║  Go to Settings and set your folder to E:\Papers                    ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
pause
