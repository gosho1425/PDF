@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  PaperLens — Start Backend (FastAPI + SQLite)
REM  Run this FIRST, then run start-frontend.bat in a separate window.
REM ─────────────────────────────────────────────────────────────────────────────
title PaperLens Backend

cd /d "%~dp0backend"

REM ── Check Python venv ────────────────────────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo  [!] Virtual environment not found. Creating it now...
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] Could not create virtual environment.
        echo  Make sure Python 3.10+ is installed: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created.
)

REM ── Activate venv ───────────────────────────────────────────────────────────
call .venv\Scripts\activate.bat

REM ── Install / update dependencies ───────────────────────────────────────────
echo.
echo  Installing / verifying Python dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)

REM ── Check .env ──────────────────────────────────────────────────────────────
if not exist ".env" (
    echo.
    echo  [!] .env file not found. Copying from .env.example...
    copy .env.example .env
    echo.
    echo  ┌─────────────────────────────────────────────────────────────────┐
    echo  │  ACTION REQUIRED: Open backend\.env and add your API key:      │
    echo  │                                                                  │
    echo  │  ANTHROPIC_API_KEY=sk-ant-your-key-here                        │
    echo  │                                                                  │
    echo  │  Get a key at: https://console.anthropic.com/                   │
    echo  └─────────────────────────────────────────────────────────────────┘
    echo.
    echo  Press any key to open .env in Notepad, then restart this script...
    pause
    notepad .env
    exit /b 0
)

REM ── Start uvicorn ───────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║  PaperLens Backend starting...                                       ║
echo  ║  API docs: http://localhost:8000/api/docs                            ║
echo  ║  Press Ctrl+C to stop.                                               ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
