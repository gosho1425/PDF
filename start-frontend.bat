@echo off
chcp 65001 >nul 2>&1
REM PaperLens - Start Frontend (Next.js dev server)
REM Run start-backend.bat FIRST in a separate window, then run this.

title PaperLens Frontend

REM Move to the frontend folder (works from any directory, even double-click)
cd /d "%~dp0frontend"
if errorlevel 1 (
    echo [ERROR] Could not change to frontend directory.
    echo Make sure you are running this from inside the paperlens folder.
    pause
    exit /b 1
)

REM --- Check Node.js is installed ---
where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Node.js is not installed or not on PATH.
    echo.
    echo Download and install Node.js LTS from:
    echo   https://nodejs.org/
    echo.
    echo After installing, restart your computer and try again.
    pause
    exit /b 1
)

REM --- Check npm is available ---
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm command not found. Reinstall Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM --- Install dependencies if node_modules is missing ---
if not exist "node_modules\" (
    echo.
    echo [INFO] node_modules not found. Installing dependencies...
    echo This only runs once and may take 1-2 minutes.
    echo.
    call npm install
    if errorlevel 1 (
        echo.
        echo [ERROR] npm install failed.
        echo Check your internet connection and try again.
        echo If it still fails, delete the node_modules folder and retry.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies installed.
)

REM --- Start Next.js dev server ---
echo.
echo ============================================================
echo   PaperLens Frontend is starting...
echo.
echo   Once you see "Ready" below, open your browser at:
echo   http://localhost:3000
echo.
echo   Keep this window open while using the app.
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

call npm run dev
if errorlevel 1 (
    echo.
    echo [ERROR] npm run dev failed.
    echo.
    echo Possible fixes:
    echo   1. Make sure start-backend.bat is running in another window
    echo   2. Check that port 3000 is not already in use:
    echo      netstat -ano ^| findstr :3000
    echo   3. Delete node_modules and run setup-windows.bat again
    pause
    exit /b 1
)

pause
