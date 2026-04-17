# PaperLens v2

Local AI-powered research paper extraction tool.
Scans a Windows folder of PDFs, extracts structured data with Claude AI,
stores results in SQLite. **No Docker, no cloud, no PostgreSQL required.**

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10 or newer | https://www.python.org/downloads/ — check "Add Python to PATH" |
| Node.js | 18 LTS or newer | https://nodejs.org/ |
| Anthropic API key | — | https://console.anthropic.com/ |

---

## First-time Setup (Windows)

**Double-click `setup-windows.bat`**

This will:
1. Check Python and Node.js are installed
2. Create a Python virtual environment in `backend/.venv/`
3. Install all Python packages (`pip install -r requirements.txt`)
4. Open `backend/.env` in Notepad — add your `ANTHROPIC_API_KEY`
5. Install Node.js packages (`npm install` in `frontend/`)

Run this **once only**. After that, use the start scripts below.

---

## Starting the App (every time)

You need **two separate Command Prompt windows** (or two double-clicks):

### Window 1 — Backend
```
Double-click: start-backend.bat
```
Wait until you see:
```
INFO: Uvicorn running on http://127.0.0.1:8000
```
**Keep this window open** while using the app.

### Window 2 — Frontend
```
Double-click: start-frontend.bat
```
Wait until you see:
```
Ready - started server on 0.0.0.0:3000
```
**Keep this window open** while using the app.

### Open the app
```
http://localhost:3000
```

> If you see a red banner saying "Backend not running", it means
> `start-backend.bat` is not running. Start it first.

---

## Manual start (alternative, if bat files don't work)

```bat
REM === Terminal 1: Backend ===
cd path\to\paperlens\backend
.venv\Scripts\activate.bat
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

REM === Terminal 2: Frontend ===
cd path\to\paperlens\frontend
npm run dev
```

---

## First use — set up your folder

1. Open http://localhost:3000
2. Click **Settings** in the nav bar
3. Enter your PDF folder path, e.g. `E:\Papers`
4. Click **Validate Path** — should show: `Folder accessible — N PDFs found`
5. Click **Save Settings**
6. Click **Scan** in the nav bar
7. Click **Scan Now** — extraction runs per-paper (30-120s each)

---

## Where your data is stored

All extracted data lives in **`backend/data/`** — this is never deleted by code updates.

```
backend/data/
    app.db            <- SQLite database: all paper records, settings, scan results
    summaries/        <- one .txt summary file per successfully processed paper
    extractions/      <- one .json extraction file per successfully processed paper
```

**These files are gitignored** — they are your data, not code.
A `git pull` will never touch them.

### What each file contains

| File | Contents |
|------|----------|
| `app.db` | Paper metadata, status, extracted fields, error messages, settings |
| `summaries/*.txt` | Human-readable summary: title, authors, material, measured values |
| `extractions/*.json` | Full structured JSON: all fields with value, unit, evidence, confidence |

---

## Backing up your data

Run **`backup-data.bat`** at any time:

```
Double-click: backup-data.bat
```

Creates a timestamped copy in `backups/paperlens-data-YYYY-MM-DD_HHMM/`
containing `app.db`, `summaries/`, and `extractions/`.

**Recommended**: back up after each large scan session.

### Restoring from backup

```bat
cd path\to\paperlens

REM Stop uvicorn first (Ctrl+C in the backend window), then:
copy backups\paperlens-data-YYYY-MM-DD_HHMM\app.db backend\data\app.db
xcopy backups\paperlens-data-YYYY-MM-DD_HHMM\summaries\ backend\data\summaries\ /E /I
xcopy backups\paperlens-data-YYYY-MM-DD_HHMM\extractions\ backend\data\extractions\ /E /I
```

---

## Updating the code (git pull)

Your extracted data is **completely safe** across code updates.

```bat
REM 1. Stop both start-backend and start-frontend windows (Ctrl+C)

REM 2. Pull new code
git pull origin paperlens-v2-mvp

REM 3. Update Python packages (run if requirements.txt changed)
cd backend
.venv\Scripts\activate.bat
pip install -r requirements.txt

REM 4. Update Node packages (run if package.json changed)
cd ..\frontend
npm install

REM 5. Start normally
cd ..
start-backend.bat   REM in one window
start-frontend.bat  REM in another window
```

Your `backend/data/app.db`, `summaries/`, and `extractions/` are untouched.
Already-processed PDFs are recognised by SHA-256 hash and always skipped.

---

## If some PDFs failed during scan

Papers that fail are kept in the database with `status=failed` and an error message.

**To retry them:**
1. Go to http://localhost:3000/scan
2. Click **Reprocess Failed**

This re-runs the AI extraction only on failed papers.
Successfully processed papers are never touched.

Common failure reasons and fixes:

| Error | Fix |
|-------|-----|
| `Anthropic API error (400): prompt is too long` | Fixed in latest version — text is now auto-chunked |
| `Invalid ANTHROPIC_API_KEY` | Check `backend/.env` — key must start with `sk-ant-` |
| `Extracted text too short` | PDF is scanned/image-only — OCR not supported |
| `Anthropic API failed after 3 attempts` | Rate limit or server issue — wait and retry |
| `No credits remaining` | Add credits at https://console.anthropic.com/settings/billing |

---

## Configuration — `backend/.env`

```env
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# LLM settings (optional)
LLM_PROVIDER=anthropic          # or: openai
LLM_MODEL=claude-sonnet-4-5     # or: claude-3-5-haiku-20241022, gpt-4o
LLM_MAX_TOKENS=8192
LLM_TEMPERATURE=0.1
LLM_TIMEOUT_SECONDS=120         # increase for slow connections

# Storage (default: backend/data/ relative to where uvicorn runs)
DATA_DIR=data

# Debug mode — shows full error details in API responses
DEBUG=false
```

---

## API Documentation

With backend running: http://localhost:8000/api/docs

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get folder path, status, PDF count |
| POST | `/api/settings` | Save folder path and custom params |
| POST | `/api/settings/validate-folder` | Check if path exists and count PDFs |
| POST | `/api/scan` | Scan folder for new PDFs |
| POST | `/api/scan/reprocess-failed` | Retry all previously failed papers |
| GET | `/api/scan/status` | Last scan result |
| GET | `/api/papers` | List papers (paginated, filterable) |
| GET | `/api/papers/{id}` | Full paper detail + extraction JSON |
| POST | `/api/papers/{id}/reprocess` | Reprocess a single paper |

---

## Project structure

```
paperlens/
    setup-windows.bat       <- First-time setup (run once)
    start-backend.bat       <- Start FastAPI backend (run first)
    start-frontend.bat      <- Start Next.js frontend (run second)
    backup-data.bat         <- Back up all extracted data
    .gitignore              <- Protects backend/data/ from git operations

    backend/
        .env.example        <- Template — copy to .env, add API key
        .env                <- YOUR config (gitignored, never overwritten)
        requirements.txt
        data/               <- YOUR data (gitignored, never overwritten)
            app.db          <- SQLite database
            summaries/      <- .txt summaries
            extractions/    <- .json extractions
        app/
            main.py         <- FastAPI application
            api/v1/         <- Endpoints: settings, scan, papers
            models/         <- SQLAlchemy models
            services/       <- Scanner, PDF reader
            llm/            <- Anthropic / OpenAI providers + schema

    frontend/
        app/                <- Next.js 14 pages
            page.tsx        <- Dashboard
            settings/       <- Folder config + custom params
            scan/           <- Trigger scan, reprocess failed
            papers/         <- Browse, search, view extractions
        lib/api.ts          <- Axios client
        components/         <- Nav, StatusBadge, BackendBanner
```

---

## Troubleshooting

### Red banner: "Backend not running"
`start-backend.bat` is not running. Start it first and wait for the
`Uvicorn running on http://127.0.0.1:8000` message.

### "Path does not exist: E:\Papers"
The backend runs on your machine and checks the path directly.
Make sure `start-backend.bat` is running, then try again.

### "TypeError: fetch failed" / blank pages
Same as above — backend is not running.

### Port 8000 or 3000 already in use
```bat
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

### setup-windows.bat shows garbled characters
Make sure you git-pulled the latest version. Old versions had an encoding
bug. Run `git pull origin paperlens-v2-mvp` to get the fix.

### npm install or pip install fails
Check your internet connection.
For pip: try `pip install -r requirements.txt --index-url https://pypi.org/simple/`
For npm: delete `frontend/node_modules/` and try again.

---

*PaperLens v2 — Windows-first local research tool — no cloud infrastructure*
