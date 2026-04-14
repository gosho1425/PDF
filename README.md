# PaperLens 🔬

**Scientific Paper Extraction & Structured Research Data Management**

PaperLens lets you upload research PDF papers, automatically extracts structured scientific data using Claude AI, and stores everything in a searchable database — ready for analysis and Bayesian optimization of experimental conditions.

---

## ⚡ Windows Quick Start

> **New to this?** Start here. Skip to [Detailed Setup](#detailed-setup-all-platforms) for explanations of every step.

**Step 1 — Install Docker Desktop**
Download and install from https://www.docker.com/products/docker-desktop/
After installing, open Docker Desktop and wait for the whale icon in the taskbar to show "Docker Desktop is running".

**Step 2 — Download this project**
If you have Git installed, open **Command Prompt** or **PowerShell** and run:
```
git clone https://github.com/gosho1425/PDF.git
cd PDF
```
If you don't have Git, click the green **Code** button on GitHub → **Download ZIP** → extract it → open a terminal inside that folder.

**Step 3 — Create your `.env` file (Windows Command Prompt)**
```cmd
copy .env.example .env
```
Or in **PowerShell**:
```powershell
Copy-Item .env.example .env
```
Or just right-click `.env.example` in File Explorer → **Copy** → **Paste** → rename the copy to `.env`.

**Step 4 — Edit `.env`**
Open `.env` in Notepad (or any text editor). Find these two lines and fill them in:
```
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```
Save the file.

**Step 5 — Start the app**
```cmd
docker compose up -d
```

**Step 6 — Open your browser**
- App: http://localhost:3000
- API docs: http://localhost:8000/api/docs

**To stop everything:**
```cmd
docker compose down
```

---

## Table of Contents

1. [What Is This Project?](#what-is-this-project)
2. [What You Need Before Starting](#what-you-need-before-starting)
3. [Key Concepts for Beginners](#key-concepts-for-beginners)
4. [Detailed Setup — All Platforms](#detailed-setup-all-platforms)
5. [Using the App](#using-the-app)
6. [Development Setup (without Docker)](#development-setup-without-docker)
7. [Architecture Overview](#architecture-overview)
8. [Data Model](#data-model)
9. [Security](#security)
10. [Project Structure](#project-structure)
11. [API Reference](#api-reference)
12. [Extraction Schema](#extraction-schema)
13. [Running Tests](#running-tests)
14. [Branch Strategy](#branch-strategy)
15. [Phase 2 Roadmap: Bayesian Optimization](#phase-2-roadmap-bayesian-optimization-integration)

---

## What Is This Project?

PaperLens is a web application that:

1. **Ingests PDF papers** — you upload one or many PDFs through a browser UI
2. **Reads them with AI** — sends the text to Claude (Anthropic's AI) running on the server
3. **Extracts structured data** — pulls out title, authors, methods, results, units, conditions
4. **Stores everything** — saves it in a database you can search and filter
5. **Exports for analysis** — download CSV or JSON, ready for Bayesian optimization

Think of it as a smart research assistant that reads your papers and fills in a spreadsheet for you — accurately, with citations back to the source text.

---

## What You Need Before Starting

### Required: Docker Desktop

**Docker** is the only thing you must install. It packages the entire application (database, AI backend, web frontend) into containers so you don't need to install Python, Node.js, or PostgreSQL separately.

| Platform | Download |
|----------|----------|
| Windows 10/11 | https://www.docker.com/products/docker-desktop/ |
| macOS (Apple Silicon or Intel) | https://www.docker.com/products/docker-desktop/ |
| Linux | https://docs.docker.com/engine/install/ |

> **Windows note:** Docker Desktop requires WSL 2 (Windows Subsystem for Linux). The installer will guide you through enabling it. If you see a prompt asking to install WSL 2, click **Yes/Install**.

After installing, **start Docker Desktop** before running any `docker compose` commands. You'll know it's ready when:
- Windows: the whale icon in the system tray says "Docker Desktop is running"
- macOS: the whale icon in the menu bar is steady (not animated)

### Required: An Anthropic API Key

PaperLens uses Claude AI to read your papers. You need an API key from Anthropic:
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to **API Keys** → **Create Key**
4. Copy the key — it starts with `sk-ant-`
5. You will paste it into your `.env` file (explained below)

> **Cost note:** Claude API calls are billed by usage. Processing one research paper typically costs a few cents. See https://www.anthropic.com/pricing for current rates.

### Optional: Git

Git lets you download ("clone") this repository with one command. If you'd rather not install it, you can use GitHub's **Download ZIP** button instead.

- Windows: https://git-scm.com/download/win (includes Git Bash)
- macOS: run `git` in Terminal — it will prompt you to install Xcode Command Line Tools
- Linux: `sudo apt install git` or `sudo dnf install git`

---

## Key Concepts for Beginners

### What is the repository folder?

When you clone or unzip this project, you get a folder (e.g., `PDF` or `paperlens`). That folder is the **repository**. It contains all the source code, configuration files, and documentation. You run all commands from inside this folder.

### What is `.env`?

`.env` is a plain text file that holds **secret configuration values** for your specific installation — things like database passwords and API keys. It is never shared or committed to Git (it's listed in `.gitignore`).

`.env.example` is a safe template with placeholder values. Your job is to copy it to `.env` and fill in the real values.

Think of `.env.example` as a blank form, and `.env` as your filled-in copy.

### What is `POSTGRES_PASSWORD`?

PostgreSQL is the database that stores all your papers and extracted data. `POSTGRES_PASSWORD` is the password for the database. You can set it to any strong password — it only needs to match between the database service and the backend. A good example: `MyStrongPassword2024!`

You don't need to remember it day-to-day. Docker manages the database internally; you only ever connect to it through the app.

### Where does `ANTHROPIC_API_KEY` go?

In your `.env` file, find this line:
```
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```
Replace `sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` with your real key from https://console.anthropic.com/.

**Security:** This key is only used by the backend server running inside Docker. It is never sent to your browser or exposed publicly. See [Security](#security) for details.

### What does `docker compose up -d` do?

It starts all the services defined in `docker-compose.yml`:
- A PostgreSQL database
- A Redis job queue
- The Python/FastAPI backend
- A Celery background worker (processes PDFs)
- The Next.js frontend

The `-d` flag means "detached" — it runs everything in the background so your terminal is free.

---

## Detailed Setup — All Platforms

### Step 1: Install Docker Desktop

See [What You Need Before Starting](#what-you-need-before-starting) above.

Verify Docker is running by opening a terminal and typing:

**Windows Command Prompt / PowerShell / macOS / Linux:**
```
docker --version
docker compose version
```
You should see version numbers, not error messages.

---

### Step 2: Get the Project Files

**If you have Git:**

*Windows Command Prompt:*
```cmd
git clone https://github.com/gosho1425/PDF.git
cd PDF
```

*PowerShell:*
```powershell
git clone https://github.com/gosho1425/PDF.git
Set-Location PDF
```

*macOS / Linux:*
```bash
git clone https://github.com/gosho1425/PDF.git
cd PDF
```

**If you don't have Git:**
1. Go to https://github.com/gosho1425/PDF
2. Click the green **Code** button → **Download ZIP**
3. Extract the ZIP file
4. Open a terminal and navigate into the extracted folder

*Windows Command Prompt — navigate into the folder:*
```cmd
cd C:\Users\YourName\Downloads\PDF-main
```

*PowerShell:*
```powershell
Set-Location C:\Users\YourName\Downloads\PDF-main
```

*macOS / Linux:*
```bash
cd ~/Downloads/PDF-main
```

---

### Step 3: Create Your `.env` File

The project ships with `.env.example` — a template. You need to copy it to `.env`.

**Windows Command Prompt:**
```cmd
copy .env.example .env
```

**PowerShell:**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

**Alternative (all platforms):** In File Explorer / Finder, right-click `.env.example` → Copy → Paste → rename the copy to `.env`.

> If you run the helper script instead, it does this copy automatically:
> - Windows PowerShell: `.\scripts\setup-env.ps1`
> - macOS / Linux: `bash scripts/setup-env.sh`

---

### Step 4: Edit `.env` — Fill in Required Values

Open `.env` in any text editor:

**Windows:** Right-click `.env` → **Open with** → **Notepad** (or VS Code if installed)

**macOS:** Open Terminal, type `open -e .env`

**Linux:** `nano .env` or `gedit .env`

Find and fill in these **two required lines**:

```
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

- Replace `CHANGE_ME_STRONG_PASSWORD` with any strong password (no spaces). Example: `PaperLens2024!`
- Replace `sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` with your real Anthropic API key

Everything else can stay as-is for a first run.

Save and close the file.

---

### Step 5: Start the Application

Make sure Docker Desktop is **open and running** first.

Open a terminal in the project folder and run:

**Windows Command Prompt:**
```cmd
docker compose up -d
```

**PowerShell:**
```powershell
docker compose up -d
```

**macOS / Linux:**
```bash
docker compose up -d
```

The first time you run this, Docker will download all the required images (this can take 5–10 minutes depending on your connection). Subsequent starts are much faster.

You should see output like:
```
✔ Container pdf-db-1        Started
✔ Container pdf-redis-1     Started
✔ Container pdf-api-1       Started
✔ Container pdf-worker-1    Started
✔ Container pdf-frontend-1  Started
```

#### Check that everything started correctly

**Windows Command Prompt / PowerShell / macOS / Linux:**
```
docker compose ps
```

All services should show `running` or `healthy`. If any show `exited`, see [Troubleshooting](#troubleshooting) below.

---

### Step 6: Open the App

Once all containers are running, open your browser:

| Service | URL | What it is |
|---------|-----|------------|
| **App (frontend)** | http://localhost:3000 | Main UI — upload papers here |
| **API docs** | http://localhost:8000/api/docs | Interactive API reference |
| **Task monitor** | http://localhost:5555 | Watch background jobs run |

---

### Step 7: Stopping and Restarting

**Stop everything (keeps your data):**

*All platforms:*
```
docker compose down
```

**Restart after stopping:**
```
docker compose up -d
```

**Stop and delete all data (full reset):**
```
docker compose down -v
```
> ⚠️ The `-v` flag deletes the database and uploaded files. Only use this if you want a completely fresh start.

---

### Troubleshooting

**"docker: command not found" or "docker is not recognized"**
→ Docker Desktop is not installed or not running. Install it from https://www.docker.com/products/docker-desktop/ and make sure it is open.

**"Cannot connect to the Docker daemon"**
→ Docker Desktop is installed but not started. Open Docker Desktop from your Start Menu / Applications folder and wait for it to show "Running".

**"error during connect" on Windows**
→ WSL 2 may not be enabled. Open Docker Desktop → Settings → General → ensure "Use the WSL 2 based engine" is checked. Or run `wsl --install` in an administrator PowerShell.

**A container exits immediately**
Run `docker compose logs api` (or `worker`, `db`, etc.) to see the error message.

The most common cause is a missing or incorrect `.env` value — especially `POSTGRES_PASSWORD` being empty.

**Port already in use**
If port 3000 or 8000 is already used by another app, edit `.env` and change `FRONTEND_PORT` or `API_PORT` to a different number, then restart.

**App opens but shows errors after uploading a PDF**
Check that `ANTHROPIC_API_KEY` in `.env` is correct and that your Anthropic account has available credits.

---

## Using the App

### 1. Upload Papers

- Go to **Upload** tab at http://localhost:3000
- Drag & drop one or multiple PDF files, or click to browse
- Each paper gets a unique ID and enters the processing queue

### 2. Monitor Processing

- The **Dashboard** shows real-time pipeline status
- Each paper progresses through: `uploaded → parsing → parsed → extracting → extracted`
- Status badges are colour-coded (green = done, yellow = in progress, red = failed)
- Failed papers can be retried with the **Reprocess** button

### 3. Review Extractions

- Click any paper to open the **detail view**
- The **Extraction Panel** shows all structured data with:
  - Confidence scores for each field (0–100%)
  - Source text snippets — the exact quote from the paper
  - "Review needed" flags for uncertain values
- Click **Edit** to manually correct any field
- All manual edits are tracked (`human_edited = true`)

### 4. Download Files

Per-paper output files:
- `summary.md` — human-readable extraction summary
- `extraction.json` — machine-readable structured data with provenance

### 5. Export for Analysis

Go to **Data Table** → click **Export CSV** or **Export JSON**.

The JSON export includes a `bo_ready` block with `X` (input variables) and `y` (output variables) split, ready for Bayesian optimization.

---

## Development Setup (without Docker)

> Use this if you want to edit the code and see live changes. Requires Python 3.11+ and Node.js 20+ installed locally, plus a running PostgreSQL and Redis instance.

### Backend

**macOS / Linux:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows Command Prompt:**
```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Windows PowerShell:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **PowerShell execution policy:** If you see "cannot be loaded because running scripts is disabled", run:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

**Set environment variables and run migrations:**

*macOS / Linux:*
```bash
# Copy env if you haven't already
cp ../.env.example ../.env
# Edit ../.env with your values, then:
set -a && source ../.env && set +a
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

*Windows Command Prompt (set each variable individually, or use the .env file):*
```cmd
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_DB=paperlens
set POSTGRES_USER=paperlens
set POSTGRES_PASSWORD=your_password_here
set ANTHROPIC_API_KEY=sk-ant-your-key-here
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

*Windows PowerShell:*
```powershell
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="paperlens"
$env:POSTGRES_USER="paperlens"
$env:POSTGRES_PASSWORD="your_password_here"
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Celery Worker

*macOS / Linux (in a separate terminal):*
```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_app:celery_app worker --loglevel=debug --queues=parse,extract,pipeline
```

*Windows Command Prompt (in a separate terminal):*
```cmd
cd backend
.venv\Scripts\activate.bat
celery -A app.workers.celery_app:celery_app worker --loglevel=debug --queues=parse,extract,pipeline
```

> **Windows note:** Celery has limited support on Windows without extra configuration. For local development on Windows, using `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` is strongly recommended over running Celery natively.

### Frontend

*All platforms (in a separate terminal):*
```
cd frontend
npm install
npm run dev
```

### Development mode with Docker (hot-reload)

This runs the full stack with live code reloading — the recommended approach for development:

```
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

*Windows Command Prompt:*
```cmd
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Architecture Overview

```
┌─────────────┐    HTTP     ┌─────────────────────────────────────┐
│  Next.js    │ ─────────▶ │         FastAPI Backend               │
│  Frontend   │             │                                       │
│  (Browser)  │             │  ┌──────────┐   ┌──────────────┐    │
└─────────────┘             │  │PDF Parser│   │  LLM Service │    │
                             │  │(pdfplumb)│   │(Claude API)  │    │
 ⚠️ NO API KEYS             │  └──────────┘   └──────────────┘    │
   in frontend!             │         │               │             │
                             │         ▼               ▼             │
                             │  ┌─────────────────────────────┐    │
                             │  │   Celery Workers (async)    │    │
                             │  └────────────┬────────────────┘    │
                             └───────────────┼─────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────┐
                    │                        │                     │
                    ▼                        ▼                     ▼
             ┌──────────┐           ┌─────────────┐       ┌──────────┐
             │PostgreSQL│           │    Redis     │       │   Files  │
             │(data)    │           │(job queue)   │       │/data/    │
             └──────────┘           └─────────────┘       │papers/   │
                                                           └──────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend | Python FastAPI | Async performance; Python ecosystem for future BO modules |
| LLM | Claude 3.5 Sonnet (server-side) | Best scientific extraction quality; secure key management |
| Database | PostgreSQL + JSONB | Structured queries + flexible scientific fields |
| Job Queue | Celery + Redis | Async processing; rate limiting; retry logic |
| Frontend | Next.js + TypeScript | Type-safe; fast; modern developer experience |
| ORM | SQLAlchemy 2.0 | Async support; mature migration tooling |
| PDF | pdfplumber + OCR fallback | Handles both digital and scanned PDFs |

---

## Data Model

```
Paper (one per PDF)
 ├── Journal
 ├── PaperAuthor → Author (many-to-many)
 └── ExtractionRecord (canonical + historical versions)
      ├── MaterialEntity       ← material/system studied
      ├── ProcessCondition     ← [BO-INPUT] fabrication parameters
      ├── MeasurementMethod    ← characterization techniques
      ├── ResultProperty       ← [BO-OUTPUT] quantitative results
      └── SourceEvidence       ← provenance: page, quote, confidence
```

### Bayesian Optimization Readiness

Every `ProcessCondition` and `ResultProperty` has a `variable_role`:
- `"input"` → controllable process parameter (X matrix)
- `"output"` → measured performance metric (y vector)
- `"contextual"` → non-controllable context

The export JSON includes a `bo_ready` block:
```json
{
  "bo_ready": {
    "X": {"annealing_temperature": {"value": 350, "unit": "°C"}},
    "y": {"TMR_ratio": {"value": 600, "unit": "%"}}
  }
}
```

---

## Security

- **API key never touches the frontend.** `ANTHROPIC_API_KEY` lives in `.env` and is only read by the backend Python process inside Docker. Your browser never sees it.
- **`.env` is gitignored.** Only `.env.example` (with placeholder values) is committed to Git. Your real `.env` file stays on your machine only.
- Input validation via Pydantic on every API endpoint.
- File type and size validation on upload (PDF only, max 100 MB).
- Duplicate detection by SHA-256 hash.
- No real secrets in any code file committed to this repository.

---

## Project Structure

```
paperlens/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI route handlers
│   │   ├── core/            # Config, logging
│   │   ├── db/              # SQLAlchemy session management
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas (including LLM output)
│   │   ├── services/
│   │   │   ├── pdf_parser.py       # Native + OCR extraction
│   │   │   ├── llm_extractor.py    # Claude API integration
│   │   │   ├── output_generator.py # summary.md + extraction.json
│   │   │   ├── paper_service.py    # DB operations
│   │   │   └── storage.py          # File storage abstraction
│   │   ├── workers/
│   │   │   ├── celery_app.py       # Celery configuration
│   │   │   └── tasks.py            # parse_pdf, extract_paper, etc.
│   │   └── main.py                 # FastAPI application
│   ├── alembic/             # Database migrations
│   ├── prompts/             # LLM prompt templates
│   └── tests/               # Unit tests
│
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages
│       │   ├── dashboard/   # Status overview
│       │   ├── upload/      # PDF upload
│       │   ├── papers/      # Paper list + detail
│       │   └── table/       # Data export table
│       ├── components/      # React components
│       ├── lib/             # API client, utilities
│       └── types/           # TypeScript type definitions
│
├── scripts/
│   ├── setup-env.ps1        # Windows PowerShell setup helper
│   └── setup-env.sh         # macOS/Linux setup helper
│
├── data/                    # Runtime data (gitignored)
│   ├── papers/{paper_id}/
│   │   ├── original.pdf
│   │   ├── summary.md
│   │   └── extraction.json
│   └── exports/
│
├── nginx/                   # Nginx config (production proxy)
├── docker-compose.yml       # Main Docker Compose config
├── docker-compose.dev.yml   # Development overrides (hot-reload)
├── .env.example             # Safe template — copy to .env
├── .gitignore               # Excludes .env, secrets, caches
└── README.md                # This file
```

---

## API Reference

Full interactive docs: http://localhost:8000/api/docs (only available when the app is running)

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/papers/upload` | Upload PDFs (multi-file) |
| POST | `/api/v1/papers/scan-folder` | Scan local folder |
| GET | `/api/v1/papers` | List papers (search, filter, sort) |
| GET | `/api/v1/papers/{id}` | Paper detail |
| PATCH | `/api/v1/papers/{id}` | Update metadata |
| POST | `/api/v1/papers/{id}/reprocess` | Re-run pipeline |
| GET | `/api/v1/papers/{id}/summary` | Download summary.md |
| GET | `/api/v1/papers/{id}/extraction-json` | Download extraction.json |
| GET | `/api/v1/extractions/{paper_id}` | Get extraction record |
| PATCH | `/api/v1/extractions/{paper_id}` | Update extraction (manual edit) |
| GET | `/api/v1/extractions/{paper_id}/evidence` | Get source provenance |
| POST | `/api/v1/export/papers` | Export CSV or JSON |

---

## Extraction Schema

The LLM is prompted to extract:

### Input Variables (X for optimization)
- Deposition method, temperature, pressure, time
- Annealing temperature, time, atmosphere
- Film thickness, rate
- Substrate, composition, dopants

### Output Variables (y for optimization)
- Conductivity / resistivity
- Magnetic: coercivity, TMR/GMR/SMR, Curie temperature, magnetization
- Electrical: mobility, carrier density, switching current
- Optical: bandgap, refractive index
- Structural: roughness, grain size, domain size

### Provenance (every important field)
- Source text (exact quote from paper)
- Page number
- Confidence score (0–1)
- Inferred vs. directly stated

---

## Running Tests

*All platforms (with virtual environment activated):*
```
cd backend
pytest tests/unit -v
pytest tests/unit -v --cov=app --cov-report=html
```

*With Docker (no local Python needed):*
```
docker compose exec api pytest tests/unit -v
```

---

## Branch Strategy

```
main                    → Production-ready code
genspark_ai_developer   → AI development branch (PR → main)
feature/xxx             → Feature branches (PR → main)
fix/xxx                 → Bug fix branches
```

---

## Phase 2 Roadmap: Bayesian Optimization Integration

The data schema is already designed for BO. Phase 2 will add:

### 1. Dataset Assembly Module (`backend/app/bo/dataset.py`)
```python
# Already possible with current schema:
X = db.query(ProcessCondition).filter_by(variable_role="input").to_dataframe()
y = db.query(ResultProperty).filter_by(variable_role="output").to_dataframe()
```

### 2. Surrogate Model (`backend/app/bo/surrogate.py`)
- Gaussian Process regression on (X, y)
- Handle missing values via imputation flags
- Per-property uncertainty quantification

### 3. Acquisition Function (`backend/app/bo/acquisition.py`)
- Expected Improvement (EI)
- Upper Confidence Bound (UCB)
- Multi-objective: Pareto front suggestions

### 4. Recommendation API (`/api/v1/bo/recommend`)
- Input: target property + constraints
- Output: recommended process conditions + uncertainty
- Integration with existing paper data

### 5. Visualization Dashboard
- Pareto front plots
- GP posterior visualization
- Recommendation history

**No database refactoring needed** — the `variable_role` field, `input_variables`/`output_variables` JSONB columns, and `bo_ready` export format are already in place.

---

## License

MIT — See LICENSE file.
