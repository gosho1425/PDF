@echo off
chcp 65001 >nul 2>&1
REM PaperLens - Start Frontend (Next.js)
REM Run start-backend.bat FIRST, then run this in a separate window.

title PaperLens Frontend

cd /d "%~dp0frontend"

REM --- Check Node.js ---
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    echo Download and install from: https://nodejs.org/ (LTS version)
    pause
    exit /b 1
)

REM --- Install dependencies if missing ---
if not exist "node_modules" (
    echo Installing Node.js dependencies (first run only)...
    npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

REM --- Start Next.js ---
echo.
echo ============================================================
echo   PaperLens Frontend starting...
echo   Open browser: http://localhost:3000
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

npm run dev
