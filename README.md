# PaperLens 🔬

**Scientific Paper Extraction & Structured Research Data Management**

PaperLens is a production-oriented web application for ingesting research paper PDFs, extracting structured scientific data using Claude AI (server-side only), and organizing results for downstream analysis — including Bayesian optimization of experimental conditions.

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
| Backend | Python FastAPI | Async performance; Python needed for future BO modules |
| LLM | Claude 3.5 Sonnet (server-side) | Best scientific extraction quality; secure key management |
| Database | PostgreSQL + JSONB | Structured queries + flexible scientific fields |
| Job Queue | Celery + Redis | Async processing; rate limiting; retry logic |
| Frontend | Next.js + TypeScript | Type-safe; fast; modern DX |
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

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- Claude API key (Anthropic)

### 1. Clone and configure

```bash
git clone <repo-url>
cd paperlens

cp .env.example .env
# Edit .env – set POSTGRES_PASSWORD and ANTHROPIC_API_KEY
nano .env
```

### 2. Start with Docker Compose

```bash
# Production-like (recommended first run):
docker compose up -d

# Development (hot-reload):
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 3. Run database migrations

```bash
# Migrations run automatically via the 'migrate' service.
# To run manually:
docker compose exec api alembic upgrade head
```

### 4. Open the app

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API docs | http://localhost:8000/api/docs |
| Celery Flower | http://localhost:5555 |

---

## Development Setup (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp ../.env.example ../.env
export $(cat ../.env | grep -v '^#' | xargs)

# Run migrations
alembic upgrade head

# Start FastAPI (requires running PostgreSQL + Redis)
uvicorn app.main:app --reload --port 8000
```

### Celery Worker

```bash
# In a separate terminal:
cd backend
celery -A app.workers.celery_app:celery_app worker --loglevel=debug --queues=parse,extract,pipeline
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Usage Guide

### 1. Upload Papers

- Go to **Upload** tab
- Drag & drop one or multiple PDF files
- Or use **Scan Local Folder** to batch-ingest from a directory

### 2. Monitor Processing

- **Dashboard** shows real-time pipeline status
- Each paper goes through: `uploaded → parsing → parsed → extracting → extracted`
- Failed papers can be re-processed with the **Reprocess** button

### 3. Review Extractions

- Click any paper to open the **detail view**
- The **Extraction Panel** shows all structured data with:
  - Confidence scores for each field
  - Source text snippets (provenance)
  - "Review needed" flags for uncertain values
- Click **Edit** to manually correct fields
- All edits are tracked (`human_edited = true`)

### 4. Download Files

Per-paper files are available:
- `summary.md` — human-readable extraction summary
- `extraction.json` — machine-readable structured data

### 5. Export for Analysis

Go to **Data Table** and click **Export CSV** or **Export JSON**.

The JSON export includes `bo_ready.X` and `bo_ready.y` for direct use in Bayesian optimization.

---

## Security

- **API key never touches the frontend.** `ANTHROPIC_API_KEY` lives in `.env` and is only accessed by the backend.
- **`.env` is gitignored.** Only `.env.example` (with placeholder values) is committed.
- Input validation via Pydantic on every endpoint.
- File type and size validation on upload.
- Duplicate detection by SHA-256 hash.
- No real secrets in any code file.

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
│   │   ├── services/        # Business logic
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
├── data/                    # Runtime data (gitignored)
│   ├── papers/{paper_id}/
│   │   ├── original.pdf
│   │   ├── summary.md
│   │   └── extraction.json
│   └── exports/
│
├── nginx/                   # Nginx config (production proxy)
├── .github/workflows/ci.yml # CI/CD
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

---

## API Reference

Full interactive docs: http://localhost:8000/api/docs

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

```bash
cd backend
pytest tests/unit -v
pytest tests/unit -v --cov=app --cov-report=html
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
