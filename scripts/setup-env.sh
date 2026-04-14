#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# PaperLens — Environment Setup Script for macOS and Linux
#
# USAGE:
#   From the project root folder, run:
#       bash scripts/setup-env.sh
#
#   Or make it executable once and run directly:
#       chmod +x scripts/setup-env.sh
#       ./scripts/setup-env.sh
#
# WHAT THIS SCRIPT DOES:
#   1. Checks you are in the right folder (project root)
#   2. If .env does not exist, copies .env.example → .env
#   3. If .env already exists, leaves it untouched
#   4. Prints clear instructions on what to edit next
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
BOLD='\033[1m'
RESET='\033[0m'

header()  { echo -e "\n${CYAN}${BOLD}$*${RESET}"; }
success() { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
info()    { echo -e "  →  $*"; }
err()     { echo -e "  ${RED}✘${RESET}  $*"; }

# ── 1. Determine project root ─────────────────────────────────────────────────
# The script lives in scripts/, so project root is one level up.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
ENV_FILE="$PROJECT_ROOT/.env"

header "PaperLens — Environment Setup"

if [[ ! -f "$ENV_EXAMPLE" ]]; then
    err "Could not find .env.example in: $PROJECT_ROOT"
    info "Make sure you are running this from inside the project folder."
    info "Example:"
    info "  cd ~/Downloads/PDF-main"
    info "  bash scripts/setup-env.sh"
    exit 1
fi

success "Project root: $PROJECT_ROOT"

# ── 2. Copy .env.example → .env (only if .env does not exist) ─────────────────

header "Checking for .env file..."

if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists — leaving it untouched."
    info "Location: $ENV_FILE"
    info "To reset: delete .env and run this script again."
else
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    success ".env created from .env.example"
    info "Location: $ENV_FILE"
fi

# ── 3. Print editing instructions ────────────────────────────────────────────

header "Next steps — edit your .env file"

echo ""
echo -e "  ${BOLD}Open .env and fill in these two required values:${RESET}"
echo ""

echo -e "  ${YELLOW}${BOLD}1. POSTGRES_PASSWORD${RESET}"
echo -e "  ${GRAY}   This is the password for the internal database.${RESET}"
echo -e "  ${GRAY}   Replace 'CHANGE_ME_STRONG_PASSWORD' with any strong password.${RESET}"
echo -e "  ${GRAY}   Example:  POSTGRES_PASSWORD=MyPaperLens2024!${RESET}"
echo ""

echo -e "  ${YELLOW}${BOLD}2. ANTHROPIC_API_KEY${RESET}"
echo -e "  ${GRAY}   Your Claude AI API key from https://console.anthropic.com/${RESET}"
echo -e "  ${GRAY}   Replace the placeholder 'sk-ant-XXXX...' with your real key.${RESET}"
echo -e "  ${GRAY}   Example:  ANTHROPIC_API_KEY=sk-ant-api03-AbCdEfGh...${RESET}"
echo ""
echo -e "  ${GRAY}   Security: this key is only used by the backend server.${RESET}"
echo -e "  ${GRAY}   It is never sent to your browser or committed to Git.${RESET}"
echo ""

# ── 4. Open editor ────────────────────────────────────────────────────────────

# Detect a suitable editor
if [[ -n "${VISUAL:-}" ]]; then
    EDITOR_CMD="$VISUAL"
elif [[ -n "${EDITOR:-}" ]]; then
    EDITOR_CMD="$EDITOR"
elif command -v code &>/dev/null; then
    EDITOR_CMD="code"
elif command -v nano &>/dev/null; then
    EDITOR_CMD="nano"
elif command -v vim &>/dev/null; then
    EDITOR_CMD="vim"
else
    EDITOR_CMD=""
fi

echo -en "  ${CYAN}Open .env for editing now?${RESET} (y/N): "
read -r OPEN_EDITOR </dev/tty || OPEN_EDITOR="n"

if [[ "$OPEN_EDITOR" =~ ^[Yy]$ ]]; then
    if [[ -n "$EDITOR_CMD" ]]; then
        info "Opening with: $EDITOR_CMD"
        $EDITOR_CMD "$ENV_FILE"
    else
        # macOS fallback — open in default text editor
        if command -v open &>/dev/null; then
            open -t "$ENV_FILE"
            info "Opened in your default text editor (macOS)."
        else
            warn "No text editor found in PATH."
            info "Open the file manually: $ENV_FILE"
        fi
    fi
else
    info "To open it later:"
    info "  nano $ENV_FILE"
    info "  # or:  code $ENV_FILE"
    info "  # or:  open -e $ENV_FILE   (macOS)"
fi

# ── 5. Docker reminder ────────────────────────────────────────────────────────

header "After editing .env — start the app"

echo ""
echo -e "  ${BOLD}Make sure Docker Desktop is running, then:${RESET}"
echo ""
echo -e "  ${GREEN}  docker compose up -d${RESET}"
echo ""
echo -e "  ${GRAY}  First run downloads images (5-10 min). Later runs start in seconds.${RESET}"
echo ""
echo -e "  ${BOLD}Once running, open:${RESET}"
echo -e "  ${GREEN}    http://localhost:3000${RESET}          ← Main app"
echo -e "  ${GREEN}    http://localhost:8000/api/docs${RESET}  ← API docs"
echo ""
echo -e "  To stop:  ${GRAY}docker compose down${RESET}"
echo ""

success "Setup script complete."
