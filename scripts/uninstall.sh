#!/bin/bash
# uninstall.sh — Completely remove Hermes Memory Wiki
# Usage: bash scripts/uninstall.sh

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────
HERMES_MEMORY_WIKI_DIR="$HOME/workspace/hermes-memory-wiki"
LAUNCH_AGENT_PLIST="$HOME/Library/LaunchAgents/com.memory-wiki.plist"
MEMORY_WIKI_CLI="$HOME/bin/memory-wiki"
SKILL_DIR="$HOME/.hermes/skills/hermes-memory-wiki"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ${NC} $1"; }
ok()    { echo -e "${GREEN}✅${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $1"; }
fail()  { echo -e "${RED}❌${NC} $1"; }

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  🧠 Hermes Memory Wiki — Uninstaller"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── Confirm ─────────────────────────────────────────────────────────────
echo "This will remove:"
echo "  • Wiki server: $HERMES_MEMORY_WIKI_DIR"
echo "  • Launch agent: $LAUNCH_AGENT_PLIST"
echo "  • CLI command: $MEMORY_WIKI_CLI"
echo "  • Context skill: $SKILL_DIR"
echo "  • Hermes cron jobs (auto-scan, backup)"
echo ""
echo -e "${YELLOW}Your conversation data in ~/.hermes/state.db is NOT touched.${NC}"
echo ""

read -rp "Continue? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    info "Aborted."
    exit 0
fi

echo ""

# ── Step 1: Stop server + unload launch agent ───────────────────────────
info "Stopping wiki server..."
if launchctl unload "$LAUNCH_AGENT_PLIST" 2>/dev/null; then
    ok "Launch agent unloaded"
else
    warn "Launch agent was not loaded"
fi

# Kill any running next processes for this project
if pgrep -f "next dev.*hermes-memory-wiki" >/dev/null 2>&1; then
    pkill -f "next dev.*hermes-memory-wiki" 2>/dev/null || true
    ok "Stopped running server process"
fi

# ── Step 2: Remove launch agent plist ───────────────────────────────────
if [[ -f "$LAUNCH_AGENT_PLIST" ]]; then
    rm "$LAUNCH_AGENT_PLIST"
    ok "Removed launch agent plist"
fi

# ── Step 3: Remove Hermes cron jobs ─────────────────────────────────────
info "Removing Hermes cron jobs..."
REMOVED=0
while IFS= read -r JOB_ID; do
    JOB_NAME=$(hermes cron list 2>/dev/null | grep "$JOB_ID" -A1 | grep "Name:" | awk '{print $2}')
    if [[ -n "$JOB_NAME" ]]; then
        hermes cron remove "$JOB_ID" 2>/dev/null && ok "Removed cron: $JOB_NAME"
        ((REMOVED++))
    fi
done < <(hermes cron list 2>/dev/null | grep -o '[a-f0-9]\{12\}')

if [[ "$REMOVED" -eq 0 ]]; then
    warn "No cron jobs found (may already be removed)"
fi

# ── Step 4: Remove CLI ──────────────────────────────────────────────────
if [[ -f "$MEMORY_WIKI_CLI" ]]; then
    rm "$MEMORY_WIKI_CLI"
    ok "Removed CLI: $MEMORY_WIKI_CLI"
fi

# ── Step 5: Remove skill ────────────────────────────────────────────────
if [[ -d "$SKILL_DIR" ]]; then
    rm -rf "$SKILL_DIR"
    ok "Removed context skill"
fi

# ── Step 6: Remove wiki directory ───────────────────────────────────────
if [[ -d "$HERMES_MEMORY_WIKI_DIR" ]]; then
    info "Removing wiki directory ($HERMES_MEMORY_WIKI_DIR)..."
    rm -rf "$HERMES_MEMORY_WIKI_DIR"
    ok "Removed wiki directory"
fi

# ── Step 7: Remove backups (optional) ───────────────────────────────────
BACKUP_DIR="$HOME/memory-wiki-backups"
if [[ -d "$BACKUP_DIR" ]]; then
    echo ""
    read -rp "Remove backups in $BACKUP_DIR? [y/N] " REMOVE_BACKUPS
    if [[ "$REMOVE_BACKUPS" == "y" || "$REMOVE_BACKUPS" == "Y" ]]; then
        rm -rf "$BACKUP_DIR"
        ok "Removed backups"
    else
        warn "Backups kept at $BACKUP_DIR"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Hermes Memory Wiki uninstalled"
echo ""
echo "  Your Hermes conversation data is untouched."
echo "  To reinstall: bash scripts/install.sh"
echo "═══════════════════════════════════════════════════════"
