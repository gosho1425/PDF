@echo off
chcp 65001 >nul 2>&1
REM PaperLens - Start Backend (FastAPI + SQLite)
REM Run this FIRST, then run start-frontend.bat in a new separate window.

title PaperLens Backend

REM Move to the backend folder
cd /d "%~dp0backend"
if errorlevel 1 (
    echo [ERROR] Could not change to backend directory.
    echo Make sure you are running this from inside the paperlens folder.
    pause
    exit /b 1
)

REM --- Check virtual environment ---
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] Python virtual environment not found.
    echo.
    echo Please run setup-windows.bat first to create it.
    pause
    exit /b 1
)

REM --- Check .env file ---
if not exist ".env" (
    echo.
    echo [INFO] .env file not found. Copying from .env.example...
    copy .env.example .env >nul
    echo.
    echo ============================================================
    echo   ACTION REQUIRED
    echo.
    echo   Open the file:  backend\.env
    echo   Find this line: ANTHROPIC_API_KEY=sk-ant-your-key-here
    echo   Replace with your real key from: https://console.anthropic.com/
    echo ============================================================
    echo.
    echo Opening .env in Notepad. Save it, then close Notepad.
    echo After closing Notepad, press any key to start the backend.
    notepad .env
    echo.
    pause
)

REM --- Activate virtual environment ---
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    echo Try running setup-windows.bat again.
    pause
    exit /b 1
)

REM --- Start uvicorn ---
echo.
echo ============================================================
echo   PaperLens Backend is starting...
echo.
echo   API docs:  http://localhost:8000/api/docs
echo   Health:    http://localhost:8000/health
echo.
echo   Keep this window open while using the app.
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
if errorlevel 1 (
    echo.
    echo [ERROR] uvicorn failed to start.
    echo.
    echo Possible fixes:
    echo   1. Check that port 8000 is not already in use:
    echo      netstat -ano ^| findstr :8000
    echo   2. Check backend\.env has a valid ANTHROPIC_API_KEY
    echo   3. Run setup-windows.bat again to reinstall dependencies
    pause
    exit /b 1
)

pause
