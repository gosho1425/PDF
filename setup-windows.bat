@echo off
chcp 65001 >nul 2>&1
REM PaperLens - First-time Windows Setup
REM Run this ONCE after cloning/downloading the project.
REM After setup, use start-backend.bat and start-frontend.bat every time.

title PaperLens Setup

echo.
echo ============================================================
echo   PaperLens - First-time Windows Setup
echo ============================================================
echo.

REM --- 1. Check Python ---
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found.
    echo.
    echo Download Python 3.10 or newer from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During install, check the box:
    echo   "Add Python to PATH"
    echo.
    echo After installing Python, restart this script.
    pause
    exit /b 1
)
python --version
echo [OK] Python found.
echo.

REM --- 2. Check Node.js ---
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Node.js not found.
    echo.
    echo Download Node.js LTS from:
    echo   https://nodejs.org/
    echo.
    echo After installing Node.js, restart this script.
    pause
    exit /b 1
)
node --version
echo [OK] Node.js found.
echo.

REM --- 3. Create Python virtual environment ---
echo [3/5] Setting up Python backend...
cd /d "%~dp0backend"

if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Could not create virtual environment.
        echo Try running: python -m venv .venv
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Installing Python packages (this may take 2-4 minutes)...
echo Note: Phase 2 includes scikit-learn and numpy for Bayesian optimization.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)
echo [OK] Python packages installed.

REM --- 4. Create .env if missing ---
if not exist ".env" (
    echo.
    echo Creating .env from template...
    copy .env.example .env >nul
    echo.
    echo ============================================================
    echo   ACTION REQUIRED - Add your Anthropic API key
    echo.
    echo   The file  backend\.env  will now open in Notepad.
    echo.
    echo   Find this line:
    echo     ANTHROPIC_API_KEY=sk-ant-your-key-here
    echo.
    echo   Replace it with your real key from:
    echo     https://console.anthropic.com/
    echo.
    echo   Save the file and close Notepad to continue setup.
    echo ============================================================
    echo.
    echo Press any key to open .env in Notepad...
    pause >nul
    notepad .env
    echo.
    echo [OK] .env configured.
) else (
    echo [OK] .env already exists.
)
echo.

REM --- 4b. Run Phase 2 migration (safe to run multiple times) ---
echo Running Phase 2 database migration (creates new optimization tables)...
python migrate_phase2.py
if errorlevel 1 (
    echo [WARN] Migration script reported an error - check above output.
    echo This is usually non-fatal. Continuing...
)
echo.

REM --- 5. Install frontend dependencies ---
echo [4/5] Installing frontend dependencies...
cd /d "%~dp0frontend"

if not exist "node_modules\" (
    echo Running npm install (this may take 1-2 minutes)...
    call npm install
    if errorlevel 1 (
        echo.
        echo [ERROR] npm install failed.
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo [OK] Frontend dependencies installed.
) else (
    echo [OK] node_modules already exists, skipping.
)
echo.

REM --- Done ---
echo [5/5] Setup complete!
echo.
echo ============================================================
echo   SETUP COMPLETE - How to start PaperLens:
echo.
echo   Step 1: Double-click  start-backend.bat   (keep window open)
echo   Step 2: Double-click  start-frontend.bat  (in a NEW window)
echo   Step 3: Open browser: http://localhost:3000
echo.
echo   In the app:
echo     - Go to Settings and set your PDF folder
echo     - Go to Scan and click Scan Now to extract literature
echo     - Go to Optimization (new!) to start BO campaigns
echo       Phase 2: Create project, seed variables, click Recommend
echo ============================================================
echo.
cd /d "%~dp0"
pause
