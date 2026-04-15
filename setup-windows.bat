@echo off
chcp 65001 >nul 2>&1
REM PaperLens - First-time Windows Setup
REM Run this ONCE, then use start-backend.bat and start-frontend.bat

title PaperLens Setup
echo.
echo ============================================================
echo   PaperLens - First-time Windows Setup
echo ============================================================
echo.

REM --- Check Python ---
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Download Python 3.10+ from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
python --version
echo [OK] Python found.
echo.

REM --- Check Node.js ---
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    echo Download Node.js LTS from: https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo [OK] Node.js found.
echo.

REM --- Backend setup ---
echo [3/5] Setting up Python backend...
cd /d "%~dp0backend"

if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
echo Installing Python packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)

if not exist ".env" (
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
    echo Opening .env in Notepad... Save and close Notepad when done.
    notepad .env
    echo.
    echo After saving .env, press any key to continue...
    pause >nul
)
echo [OK] Backend ready.
echo.

REM --- Frontend setup ---
echo [4/5] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
) else (
    echo [OK] node_modules already exists, skipping npm install.
)
echo [OK] Frontend ready.
echo.

REM --- Done ---
echo [5/5] Setup complete!
echo.
echo ============================================================
echo   HOW TO START PAPERLENS:
echo.
echo   Window 1: double-click  start-backend.bat   (keep open)
echo   Window 2: double-click  start-frontend.bat  (keep open)
echo   Browser:  http://localhost:3000
echo.
echo   Then go to Settings and enter your folder: E:\Papers
echo ============================================================
echo.
cd /d "%~dp0"
pause
