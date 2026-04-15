# 🔬 PaperLens v2 — Windows-First Local Research Tool

Extract structured scientific data from PDF research papers using AI.  
**No Docker · No PostgreSQL · No Redis · No cloud infrastructure required.**  
Runs directly on Windows with Python and Node.js.

---

## What It Does

1. You point PaperLens at a folder containing PDF papers.
2. It recursively finds all PDFs, computes SHA-256 for each, and skips already-processed files.
3. New PDFs are read by `pdfplumber` and sent to Claude (or GPT-4o) for structured extraction.
4. Results are stored in:
   - `data/app.db` — SQLite database
   - `data/summaries/<name>.txt` — human-readable summary
   - `data/extractions/<id>.json` — full structured JSON
5. The UI lets you browse all papers, view extracted variables, and re-process individual files.

### Extracted Fields

| Category | Fields |
|----------|--------|
| **Bibliographic** | Title, authors, journal, year, DOI, impact factor |
| **Material info** | Material/compound, substrate, crystal structure, film geometry |
| **Input variables** | Deposition method/temperature, sputtering power, working pressure, gas composition, film thickness, annealing conditions, oxygen pressure, laser fluence, target composition |
| **Output variables** | Tc, Jc, RRR, resistivity, surface roughness, crystallinity, lattice parameter, Hc2, coherence length, penetration depth, band gap |
| **Evidence** | Every value includes: evidence text (verbatim quote), page number, confidence score (0–1) |

Custom parameters can be added in the Settings page — the LLM will extract them for every future paper.

---

## Repository Structure

```
paperlens/
├── backend/                  ← FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── api/v1/           ← REST endpoints
│   │   │   ├── papers_router.py
│   │   │   ├── scan_router.py
│   │   │   └── settings_router.py
│   │   ├── core/
│   │   │   ├── config.py     ← pydantic-settings (reads .env)
│   │   │   └── logging.py
│   │   ├── db/
│   │   │   └── database.py   ← SQLAlchemy engine + session
│   │   ├── llm/
│   │   │   ├── base.py       ← abstract LLMProvider + data classes
│   │   │   ├── factory.py    ← provider selection
│   │   │   ├── schema.py     ← prompt builder + response parser
│   │   │   └── providers/
│   │   │       ├── anthropic_provider.py
│   │   │       └── openai_provider.py
│   │   ├── models/           ← SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── pdf_reader.py ← pdfplumber + PyMuPDF fallback
│   │   │   ├── scanner.py    ← core ingestion engine
│   │   │   └── settings_service.py
│   │   └── main.py           ← FastAPI app + CORS + startup
│   ├── requirements.txt
│   └── .env.example          ← copy to .env and add API key
│
├── frontend/                 ← Next.js 14 + Tailwind CSS
│   ├── app/
│   │   ├── page.tsx          ← Dashboard
│   │   ├── scan/page.tsx     ← Scan controls
│   │   ├── papers/
│   │   │   ├── page.tsx      ← Paper list
│   │   │   └── [id]/page.tsx ← Paper detail + extractions
│   │   └── settings/page.tsx ← Folder + custom params config
│   ├── components/
│   │   ├── layout/Nav.tsx
│   │   └── ui/
│   │       ├── StatusBadge.tsx
│   │       └── Toaster.tsx
│   ├── lib/api.ts            ← axios API client
│   └── types/index.ts        ← TypeScript interfaces
│
└── data/                     ← Created automatically on first run
    ├── app.db                ← SQLite database
    ├── summaries/            ← .txt summary files
    └── extractions/          ← .json extraction files
```

---

## Windows Setup Guide (Beginner-Friendly)

### Prerequisites

Install these if you haven't already:

| Tool | Download | Version |
|------|----------|---------|
| Python | https://python.org/downloads | 3.10+ |
| Node.js | https://nodejs.org | 18+ LTS |
| Git | https://git-scm.com | any |

> **Tip:** During Python install, check **"Add Python to PATH"**.

---

### Step 1 — Clone the Repository

Open **Command Prompt** or **PowerShell**:

```cmd
git clone https://github.com/gosho1425/PDF.git paperlens
cd paperlens
git checkout paperlens-v2-mvp
```

---

### Step 2 — Backend Setup

```cmd
cd backend

REM Create a virtual environment
python -m venv .venv

REM Activate it (Command Prompt)
.venv\Scripts\activate.bat

REM Or activate in PowerShell:
REM .venv\Scripts\Activate.ps1

REM Install dependencies
pip install -r requirements.txt
```

**Configure your API key:**

```cmd
REM Windows copy
copy .env.example .env
notepad .env
```

Edit `.env` — set your Anthropic API key:

```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

Get a key at: https://console.anthropic.com

---

### Step 3 — Frontend Setup

Open a **second terminal** (keep the backend terminal open):

```cmd
cd paperlens\frontend
npm install
```

---

### Step 4 — Start Everything

**Terminal 1 — Backend:**

```cmd
cd paperlens\backend
.venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO: PaperLens v2.0.0 starting…
INFO: Database: data\app.db
INFO: LLM: anthropic / claude-sonnet-4-5
INFO: Ready — API docs at http://localhost:8000/api/docs
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 — Frontend:**

```cmd
cd paperlens\frontend
npm run dev
```

You should see:
```
  ▲ Next.js 14.x.x
  - Local: http://localhost:3000
```

---

### Step 5 — Use the App

1. Open **http://localhost:3000** in your browser.
2. Click **Settings** in the top menu.
3. Enter your PDF folder path, e.g. `C:\Users\YourName\Documents\Papers`
4. Click **Validate Path** → **Save Settings**.
5. Click **Scan** → **Scan Now**.
6. Wait for extraction (30–120 seconds per paper).
7. Click **Papers** to see results.

---

## Switching LLM Provider

Edit `backend/.env`:

```env
# Use OpenAI instead of Anthropic
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-openai-key-here
```

Restart the backend:

```cmd
REM Press Ctrl+C in backend terminal, then:
uvicorn app.main:app --reload
```

---

## Adding Custom Extraction Parameters

In the Settings page, scroll to **Custom Extraction Parameters** and click **Add Parameter**:

| Field | Example |
|-------|---------|
| Name | `vortex_density` |
| Label | `Vortex Density` |
| Unit | `cm⁻²` |
| Role | `output` (measured result) |
| Description | `Vortex density from magnetic imaging` |

These parameters are added to every LLM extraction prompt for all future scans.

---

## API Documentation

Interactive API docs (Swagger UI):  
**http://localhost:8000/api/docs**

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get current settings + folder status |
| POST | `/api/settings` | Update folder path or custom parameters |
| POST | `/api/settings/validate-folder` | Check if a folder path is valid |
| GET | `/api/settings/llm` | Show LLM config (no API keys) |
| POST | `/api/scan` | Run folder scan (blocking) |
| GET | `/api/scan/status` | Last scan result |
| GET | `/api/papers` | List papers (filterable, searchable) |
| GET | `/api/papers/{id}` | Full paper detail with extraction |
| GET | `/api/papers/{id}/summary` | Plain-text summary file |
| POST | `/api/papers/{id}/reprocess` | Re-run LLM for one paper |
| DELETE | `/api/papers/{id}` | Delete paper + output files |
| GET | `/health` | Health check |

---

## Troubleshooting

### "No module named 'app'"

Make sure you're running `uvicorn` from the `backend/` directory:

```cmd
cd paperlens\backend
uvicorn app.main:app --reload
```

### "ANTHROPIC_API_KEY is not set"

Your `backend/.env` file is missing or the key is wrong:

```cmd
type backend\.env   REM Check the file exists and has the key
```

### "pdfplumber failed"

Some PDFs are scanned images without text layer. OCR is not included in MVP.  
Try using Adobe Acrobat's "Make Searchable PDF" feature first.

### Frontend can't reach backend

Check that:
1. Backend is running on port 8000 (`http://localhost:8000/health` should return `{"status":"ok"}`)
2. No firewall is blocking port 8000

### Port 8000 already in use

```cmd
REM Use a different port
uvicorn app.main:app --reload --port 8001
```

Then update the frontend's API URL:

```cmd
REM In frontend directory
set NEXT_PUBLIC_API_URL=http://localhost:8001
npm run dev
```

---

## What Was Removed from v1 (Docker version)

| v1 Component | v2 Replacement | Reason |
|---|---|---|
| Docker / Docker Compose | Run directly with Python + Node.js | No setup complexity on Windows |
| PostgreSQL | SQLite (`data/app.db`) | No server needed, file-based |
| Redis | In-process state (`dict`) | No broker needed for sync scans |
| Celery workers | Direct function call in API | Simpler, blocking scan per request |
| Alembic migrations | `Base.metadata.create_all()` | Schema auto-created on startup |
| nginx | Next.js dev server | Direct `npm run dev` |
| Flower (Celery monitor) | Scan status endpoint | Lightweight alternative |
| Docker bind mounts | User-configured folder path in Settings UI | Works with any Windows path |
| INGEST_DIR env var | `paper_folder` in SQLite settings | Configurable at runtime |

---

## Development Notes

- **Backend auto-reload:** `--reload` flag watches for file changes.
- **Database location:** `backend/data/app.db` (relative to where uvicorn runs).
- **Output files:** `backend/data/summaries/` and `backend/data/extractions/`.
- **API key security:** Keys live in `backend/.env` — never sent to the Next.js frontend.
- **Deduplication:** SHA-256 hash prevents re-processing the same file.
- **Bayesian optimization:** Input/output variable separation is designed for BO workflows.

---

## License

MIT
