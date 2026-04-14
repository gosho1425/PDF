# Contributing to PaperLens

This guide explains how to set up a development environment on Windows, macOS, and Linux.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Common Commands — Cross-Platform Reference](#common-commands--cross-platform-reference)
4. [Docker-Based Development (Recommended)](#docker-based-development-recommended)
5. [Native Development (Without Docker)](#native-development-without-docker)
6. [Running Tests](#running-tests)
7. [Code Style](#code-style)
8. [Pull Request Process](#pull-request-process)

---

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop/ |
| Git | Any recent | https://git-scm.com/ |
| Python | 3.11+ | https://www.python.org/downloads/ (only for native dev) |
| Node.js | 20 LTS | https://nodejs.org/ (only for native dev) |

---

## Initial Setup

**All platforms:** Run the setup helper script to create your `.env` file.

*Windows PowerShell:*
```powershell
.\scripts\setup-env.ps1
```

*macOS / Linux:*
```bash
bash scripts/setup-env.sh
```

Then edit `.env` and fill in:
- `POSTGRES_PASSWORD` — any strong password
- `ANTHROPIC_API_KEY` — your key from https://console.anthropic.com/

---

## Common Commands — Cross-Platform Reference

Many Unix tutorials use commands that don't work in Windows Command Prompt. Here is a translation table:

### File operations

| Task | macOS / Linux | Windows CMD | Windows PowerShell |
|------|--------------|-------------|-------------------|
| Copy a file | `cp src dst` | `copy src dst` | `Copy-Item src dst` |
| Move / rename | `mv src dst` | `move src dst` | `Move-Item src dst` |
| Delete a file | `rm file` | `del file` | `Remove-Item file` |
| Delete a folder | `rm -rf folder` | `rd /s /q folder` | `Remove-Item -Recurse -Force folder` |
| List files | `ls -la` | `dir` | `Get-ChildItem` or `ls` |
| Print file content | `cat file.txt` | `type file.txt` | `Get-Content file.txt` |
| Show current folder | `pwd` | `cd` | `Get-Location` or `pwd` |
| Create folder | `mkdir -p a/b` | `mkdir a\b` | `New-Item -ItemType Directory -Force a\b` |

### Environment variables

| Task | macOS / Linux | Windows CMD | Windows PowerShell |
|------|--------------|-------------|-------------------|
| Set a variable | `export KEY=value` | `set KEY=value` | `$env:KEY="value"` |
| Read a variable | `echo $KEY` | `echo %KEY%` | `$env:KEY` |
| Load from file | `source .env` or `set -a; . .env; set +a` | *(not built-in — use scripts)* | *(not built-in — use scripts)* |

> **Tip for Windows developers:** When running the backend locally (without Docker), set each environment variable individually in your terminal session, or use the `.env` file approach described in the [Native Development](#native-development-without-docker) section.

### Python virtual environments

| Task | macOS / Linux | Windows CMD | Windows PowerShell |
|------|--------------|-------------|-------------------|
| Create venv | `python -m venv .venv` | `python -m venv .venv` | `python -m venv .venv` |
| Activate venv | `source .venv/bin/activate` | `.venv\Scripts\activate.bat` | `.\.venv\Scripts\Activate.ps1` |
| Deactivate | `deactivate` | `deactivate` | `deactivate` |

> **PowerShell execution policy:** If activation fails with a "cannot be loaded" error, run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## Docker-Based Development (Recommended)

This is the easiest approach for all platforms, including Windows, because Docker handles all the environment differences.

### Start full stack with hot-reload

*All platforms:*
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This starts:
- Backend with `--reload` (code changes restart automatically)
- Celery worker in debug mode
- Frontend with `npm run dev` (Next.js hot-reload)

### Useful Docker commands

*All platforms:*
```bash
# See logs for a specific service
docker compose logs api
docker compose logs worker
docker compose logs frontend

# Follow logs in real time
docker compose logs -f api

# Restart one service
docker compose restart api

# Run a command inside a container
docker compose exec api python -m pytest tests/unit -v
docker compose exec api alembic upgrade head

# Stop everything
docker compose down

# Stop and remove all data (full reset)
docker compose down -v
```

### Check service health

```
docker compose ps
```

All services should show `healthy`. If a service shows `exited`, check its logs:
```
docker compose logs <service-name>
```

---

## Native Development (Without Docker)

Use this if you want faster iteration without container build times. You still need PostgreSQL and Redis running (you can run just those via Docker while running the rest natively).

### Run only the infrastructure via Docker

```
docker compose up -d db redis
```

This starts just the database and Redis, leaving them available at `localhost:5432` and `localhost:6379`.

### Backend (Python)

**macOS / Linux:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment (once per terminal session)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=paperlens
export POSTGRES_USER=paperlens
export POSTGRES_PASSWORD=your_password
export ANTHROPIC_API_KEY=sk-ant-your-key

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

**Windows Command Prompt:**
```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt

set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_DB=paperlens
set POSTGRES_USER=paperlens
set POSTGRES_PASSWORD=your_password
set ANTHROPIC_API_KEY=sk-ant-your-key

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Windows PowerShell:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="paperlens"
$env:POSTGRES_USER="paperlens"
$env:POSTGRES_PASSWORD="your_password"
$env:ANTHROPIC_API_KEY="sk-ant-your-key"

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Celery Worker

> **Windows note:** Celery on Windows requires `--pool=solo` to work without errors. Background task processing is functional but limited to a single concurrent worker.

**macOS / Linux (in a new terminal):**
```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_app:celery_app worker \
  --loglevel=debug \
  --queues=parse,extract,pipeline
```

**Windows (in a new terminal):**
```cmd
cd backend
.venv\Scripts\activate.bat
celery -A app.workers.celery_app:celery_app worker ^
  --loglevel=debug ^
  --queues=parse,extract,pipeline ^
  --pool=solo
```

### Frontend (Node.js)

*All platforms (in a new terminal):*
```
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000

---

## Running Tests

### With Docker (no local Python needed)

*All platforms:*
```
docker compose exec api pytest tests/unit -v
```

### With local Python (virtual environment active)

**macOS / Linux:**
```bash
cd backend
source .venv/bin/activate
pytest tests/unit -v
pytest tests/unit -v --cov=app --cov-report=html
```

**Windows Command Prompt:**
```cmd
cd backend
.venv\Scripts\activate.bat
pytest tests/unit -v
```

**Windows PowerShell:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/unit -v
```

---

## Code Style

- **Python:** follows PEP 8; use `black` for formatting, `ruff` for linting
- **TypeScript:** strict mode enabled; ESLint configured in `frontend/.eslintrc`
- **Commits:** use conventional commit format: `type(scope): message`
  - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

## Pull Request Process

1. Fork the repo or create a feature branch: `feature/your-feature-name`
2. Make your changes with clear commits
3. Run tests: `pytest tests/unit -v`
4. Open a PR against `main`
5. Fill in the PR template with a description of what changed and why
