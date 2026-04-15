#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# PaperLens – macOS/Linux environment diagnostics
# Run from the project root: bash scripts/check-env.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  PaperLens – Environment Diagnostics${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

ERRORS=0

# ── 1. Docker check ──────────────────────────────────────────────────────────
echo -e "${YELLOW}1. Docker${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "   ${RED}✗ Docker not found. Install from https://www.docker.com/products/docker-desktop/${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "   ${GREEN}✓ $(docker --version)${NC}"
    if ! docker info &>/dev/null; then
        echo -e "   ${RED}✗ Docker daemon is not running. Start Docker Desktop.${NC}"
        ERRORS=$((ERRORS+1))
    else
        echo -e "   ${GREEN}✓ Docker daemon is running.${NC}"
    fi
fi
echo ""

# ── 2. .env file check ───────────────────────────────────────────────────────
echo -e "${YELLOW}2. .env file${NC}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "   ${RED}✗ .env file is MISSING.${NC}"
    echo -e "   ${NC}  → Run: cp .env.example .env${NC}"
    echo -e "   ${NC}  → Then edit .env and fill in POSTGRES_PASSWORD and ANTHROPIC_API_KEY${NC}"
    ERRORS=$((ERRORS+1))
    exit 1
else
    echo -e "   ${GREEN}✓ .env file exists.${NC}"
fi
echo ""

# Parse .env
get_env_val() {
    grep -E "^${1}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'"
}

# ── 3. POSTGRES_PASSWORD ─────────────────────────────────────────────────────
echo -e "${YELLOW}3. POSTGRES_PASSWORD${NC}"
PG_PASS=$(get_env_val "POSTGRES_PASSWORD")
if [ -z "$PG_PASS" ] || echo "$PG_PASS" | grep -qi "CHANGE_ME"; then
    echo -e "   ${RED}✗ POSTGRES_PASSWORD is empty or still the placeholder.${NC}"
    echo -e "   ${NC}  → Edit .env and set a real password: POSTGRES_PASSWORD=PaperLens2024!${NC}"
    echo -e "   ${YELLOW}  ⚠  This is the most common reason pdf-db-1 fails to start.${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "   ${GREEN}✓ POSTGRES_PASSWORD is set (${#PG_PASS} chars).${NC}"
fi
echo ""

# ── 4. ANTHROPIC_API_KEY ─────────────────────────────────────────────────────
echo -e "${YELLOW}4. ANTHROPIC_API_KEY${NC}"
API_KEY=$(get_env_val "ANTHROPIC_API_KEY")
if [ -z "$API_KEY" ] || echo "$API_KEY" | grep -q "XXXX"; then
    echo -e "   ${RED}✗ ANTHROPIC_API_KEY is empty or still the placeholder.${NC}"
    echo -e "   ${NC}  → Get your key from https://console.anthropic.com/ (starts with sk-ant-)${NC}"
    echo -e "   ${NC}  → The app starts without it, but PDF extraction will fail.${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "   ${GREEN}✓ ANTHROPIC_API_KEY is set (${API_KEY:0:10}...).${NC}"
fi
echo ""

# ── 5. HOST_PAPER_DIR ────────────────────────────────────────────────────────
echo -e "${YELLOW}5. HOST_PAPER_DIR (PDF ingestion folder)${NC}"
PAPER_DIR=$(get_env_val "HOST_PAPER_DIR")
if [ -z "$PAPER_DIR" ]; then
    echo -e "   ${YELLOW}⚠  HOST_PAPER_DIR is not set.${NC}"
    echo -e "   ${NC}  → Fallback ./data/ingest will be used (empty folder).${NC}"
    echo -e "   ${NC}  → Set HOST_PAPER_DIR=/path/to/your/pdfs in .env to ingest real files.${NC}"
elif [ ! -d "$PAPER_DIR" ]; then
    echo -e "   ${RED}✗ HOST_PAPER_DIR='$PAPER_DIR' does not exist on this machine.${NC}"
    echo -e "   ${NC}  → Create the folder or update HOST_PAPER_DIR in .env.${NC}"
    ERRORS=$((ERRORS+1))
else
    PDF_COUNT=$(find "$PAPER_DIR" -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "   ${GREEN}✓ HOST_PAPER_DIR='$PAPER_DIR' exists ($PDF_COUNT PDF file(s) found).${NC}"
fi
echo ""

# ── 6. Stale volume check ────────────────────────────────────────────────────
echo -e "${YELLOW}6. Stale Docker volume check${NC}"
if docker volume ls --format "{{.Name}}" 2>/dev/null | grep -q "pdf_postgres_data"; then
    echo -e "   ${CYAN}ℹ  Volume 'pdf_postgres_data' already exists.${NC}"
    echo -e "   ${NC}  → If you changed POSTGRES_PASSWORD after a previous run, reset the volume:${NC}"
    echo -e "   ${NC}     docker compose down -v   (WARNING: deletes all stored data)${NC}"
    echo -e "   ${NC}     docker compose up -d${NC}"
else
    echo -e "   ${GREEN}✓ No existing volume — fresh start.${NC}"
fi
echo ""

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}  All checks passed. Run: docker compose up -d${NC}"
else
    echo -e "${RED}  $ERRORS issue(s) found above. Fix them, then run: docker compose up -d${NC}"
fi
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""
exit "$ERRORS"
