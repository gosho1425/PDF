@echo off
chcp 65001 >nul 2>&1
REM PaperLens - Start Backend (FastAPI)
REM Run this FIRST, then run start-frontend.bat in a separate window.

title PaperLens Backend

cd /d "%~dp0backend"

REM --- Check venv ---
if not exist ".venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found. Run setup-windows.bat first.
    pause
    exit /b 1
)

REM --- Check .env ---
if not exist ".env" (
    echo [!] .env file not found. Copying from .env.example...
    copy .env.example .env
    echo.
    echo ============================================================
    echo   ACTION REQUIRED: Add your API key to backend\.env
    echo.
    echo   Edit this line:
    echo   ANTHROPIC_API_KEY=sk-ant-your-key-here
    echo.
    echo   Get a key at: https://console.anthropic.com/
    echo ============================================================
    echo.
    notepad .env
    exit /b 0
)

REM --- Activate venv ---
call .venv\Scripts\activate.bat

REM --- Start uvicorn ---
echo.
echo ============================================================
echo   PaperLens Backend starting...
echo   API docs: http://localhost:8000/api/docs
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
