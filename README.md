# PaperLens v2

Local AI-powered research paper extraction tool.  
Scans a folder of PDFs, extracts structured data with Claude AI, stores results in SQLite.  
**No Docker, no PostgreSQL, no Redis required — runs entirely on Windows.**

---

## Quick Start (Windows)

### Prerequisites
| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10+ | https://www.python.org/downloads/ (check "Add to PATH") |
| Node.js | 18+ LTS | https://nodejs.org/ |
| Anthropic API key | — | https://console.anthropic.com/ |

### One-time Setup
1. Download / clone the repository
2. Double-click **`setup-windows.bat`**  
   - Creates Python virtual environment, installs all dependencies  
   - Opens `backend/.env` in Notepad — add your `ANTHROPIC_API_KEY`  
   - Installs Node.js packages

### Start the App (every time)
Open **two** Command Prompt windows:

**Window 1 — Backend:**
```bat
start-backend.bat
```
Wait until you see: `Uvicorn running on http://127.0.0.1:8000`

**Window 2 — Frontend:**
```bat
start-frontend.bat
```
Wait until you see: `Ready — started server on 0.0.0.0:3000`

**Open your browser:** http://localhost:3000

---

## Manual Setup (alternative)

```bat
REM === Backend ===
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
notepad .env          REM <-- add ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload

REM === Frontend (new window) ===
cd frontend
npm install
npm run dev
```

---

## Configuration

### `backend/.env`

```env
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional — change LLM
LLM_PROVIDER=anthropic          # or: openai
LLM_MODEL=claude-sonnet-4-5     # or: gpt-4o, gpt-4o-mini
LLM_MAX_TOKENS=8192
LLM_TEMPERATURE=0.1
LLM_TIMEOUT_SECONDS=120

# Optional — use OpenAI instead
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o
# OPENAI_API_KEY=sk-your-openai-key

# Storage location (default: backend/data/)
DATA_DIR=data
```

### Setting the Paper Folder

1. Open http://localhost:3000/settings
2. Enter your folder path, e.g. `E:\Papers`
3. Click **Validate Path** → should show ✓ with PDF count
4. Click **Save Settings**
5. Go to http://localhost:3000/scan and click **Scan Now**

> **Why does "Validate Path" say "Path does not exist"?**  
> The backend runs on the same machine as your PDFs.  
> If you see this error, make sure the backend is running AND the path is correct.  
> Windows paths with backslashes (`E:\Papers`) work directly.

---

## Troubleshooting

### ✗ "TypeError: fetch failed" or "Backend not running"

The red banner at the top of the page appears when the backend is not running.

**Fix:**
```bat
cd backend
.venv\Scripts\activate.bat
uvicorn app.main:app --reload
```

### ✗ "Path does not exist: E:\Papers"

- The backend must be running on the **same machine** as the PDF folder  
- Check the path in Settings — try copy-pasting from Windows Explorer  
- Network drives (e.g. `\\server\share`) may require additional permissions

### ✗ "pip install failed" / "npm install failed"

- Check your internet connection  
- For pip: try `pip install -r requirements.txt --index-url https://pypi.org/simple/`  
- For npm: try deleting `frontend/node_modules/` and running `npm install` again

### ✗ Port 8000 or 3000 already in use

```bat
REM Kill the process on port 8000:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## Project Structure

```
paperlens/
├── setup-windows.bat       ← First-time setup
├── start-backend.bat       ← Start FastAPI (run first)
├── start-frontend.bat      ← Start Next.js (run second)
│
├── backend/
│   ├── .env.example        ← Copy to .env, add API key
│   ├── requirements.txt
│   ├── data/
│   │   ├── app.db          ← SQLite database
│   │   ├── summaries/      ← .txt summaries per paper
│   │   └── extractions/    ← .json extractions per paper
│   └── app/
│       ├── main.py         ← FastAPI app
│       ├── api/v1/         ← Endpoints: settings, scan, papers
│       ├── models/         ← SQLAlchemy models
│       ├── services/       ← Scanner, PDF reader
│       └── llm/            ← Anthropic / OpenAI providers
│
└── frontend/
    ├── app/                ← Next.js pages
    │   ├── page.tsx        ← Dashboard
    │   ├── settings/       ← Folder config + custom params
    │   ├── scan/           ← Trigger scan + results
    │   └── papers/         ← Browse + detail view
    ├── lib/api.ts          ← Axios client → /api/proxy/*
    └── components/         ← Nav, StatusBadge, BackendBanner
```

---

## API Docs

With the backend running: http://localhost:8000/api/docs

Key endpoints:
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get folder path and status |
| POST | `/api/settings` | Save folder path |
| POST | `/api/settings/validate-folder` | Check if a path exists and count PDFs |
| POST | `/api/scan` | Scan folder and process new PDFs |
| GET | `/api/scan/status` | Last scan result |
| GET | `/api/papers` | List papers (pagination + filter) |
| GET | `/api/papers/{id}` | Paper detail + extraction JSON |
| POST | `/api/papers/{id}/reprocess` | Re-run LLM extraction |

---

## Supported LLM Providers

| Provider | Models | Config |
|----------|--------|--------|
| Anthropic (default) | `claude-sonnet-4-5`, `claude-3-5-haiku-20241022` | `LLM_PROVIDER=anthropic` |
| OpenAI | `gpt-4o`, `gpt-4o-mini` | `LLM_PROVIDER=openai` |

Switch by editing `backend/.env` — no code changes required.

---

## What Gets Extracted

For each PDF, PaperLens extracts:

- **Bibliographic**: title, authors, journal, year, DOI, impact factor
- **Material**: composition, structure, deposition conditions
- **Experimental results**: Tc, Hc2, resistivity, etc.  
- **Evidence**: page numbers, quoted text, confidence scores
- **Custom parameters**: add your own in Settings → Custom Extraction Parameters

Results are saved as:
- `data/extractions/<hash>.json` — full structured JSON
- `data/summaries/<hash>.txt` — human-readable summary

---

*PaperLens v2 · Windows-first · No cloud infrastructure required*
