@echo off
chcp 65001 >nul 2>&1
REM PaperLens - Backup extracted data
REM Run this to create a timestamped backup of all your extracted results.
REM Safe to run while the app is NOT scanning (stop uvicorn first for DB safety).

title PaperLens Backup

cd /d "%~dp0"

REM --- Determine backup filename with timestamp ---
for /f "tokens=1-6 delims=/:. " %%a in ("%date% %time%") do (
    set YYYY=%%a
    set MM=%%b
    set DD=%%c
    set HH=%%d
    set MIN=%%e
)
REM Handle locale differences - try numeric date detection
echo %YYYY% | findstr /r "^[0-9][0-9][0-9][0-9]$" >nul 2>&1
if errorlevel 1 (
    REM Fallback: use a simple counter
    set STAMP=backup
) else (
    set STAMP=%YYYY%-%MM%-%DD%_%HH%%MIN%
)

set BACKUP_DIR=backups
set BACKUP_NAME=paperlens-data-%STAMP%
set BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%

echo.
echo ============================================================
echo   PaperLens Data Backup
echo   Destination: %BACKUP_PATH%
echo ============================================================
echo.

REM --- Check data folder exists ---
if not exist "backend\data\" (
    echo [ERROR] backend\data\ folder not found.
    echo Have you run the app and scanned at least one PDF?
    pause
    exit /b 1
)

REM --- Create backup directory ---
if not exist "%BACKUP_DIR%\" mkdir "%BACKUP_DIR%"
mkdir "%BACKUP_PATH%"

REM --- Copy database ---
echo [1/3] Backing up database (app.db)...
if exist "backend\data\app.db" (
    copy "backend\data\app.db" "%BACKUP_PATH%\app.db" >nul
    echo [OK] app.db copied.
) else (
    echo [WARN] app.db not found (no papers scanned yet).
)

REM --- Copy summaries ---
echo [2/3] Backing up summaries...
if exist "backend\data\summaries\" (
    xcopy "backend\data\summaries\" "%BACKUP_PATH%\summaries\" /E /I /Q >nul 2>&1
    echo [OK] summaries/ copied.
) else (
    echo [WARN] summaries/ folder not found.
)

REM --- Copy extractions ---
echo [3/3] Backing up extractions (JSON)...
if exist "backend\data\extractions\" (
    xcopy "backend\data\extractions\" "%BACKUP_PATH%\extractions\" /E /I /Q >nul 2>&1
    echo [OK] extractions/ copied.
) else (
    echo [WARN] extractions/ folder not found.
)

echo.
echo ============================================================
echo   Backup complete!
echo   Location: %CD%\%BACKUP_PATH%
echo.
echo   Contents:
echo     app.db         - SQLite database (all paper records)
echo     summaries/     - .txt summaries per paper
echo     extractions/   - .json structured extractions per paper
echo.
echo   To restore: copy these files back to backend\data\
echo     copy %BACKUP_PATH%\app.db backend\data\app.db
echo     xcopy %BACKUP_PATH%\summaries\ backend\data\summaries\ /E /I
echo     xcopy %BACKUP_PATH%\extractions\ backend\data\extractions\ /E /I
echo ============================================================
echo.
pause
