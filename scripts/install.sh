#!/bin/bash
# install.sh — One-click installer for hermes-memory-wiki
# Usage: curl -fsSL https://raw.githubusercontent.com/kiranklabs/hermes-memory-wiki/main/install.sh | bash
# Or:    git clone https://github.com/kiranklabs/hermes-memory-wiki.git && cd hermes-memory-wiki && bash scripts/install.sh

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────
HERMES_MEMORY_WIKI_DIR="$HOME/workspace/hermes-memory-wiki"
HERMES_STATE_DB="$HOME/.hermes/state.db"
HERMES_SKILLS_DIR="$HOME/.hermes/skills"
LAUNCH_AGENT_PLIST="$HOME/Library/LaunchAgents/com.memory-wiki.plist"
MEMORY_WIKI_CLI="$HOME/bin/memory-wiki"
PORT=9876

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

# ── Pre-flight checks ────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  🧠 Hermes Memory Wiki — Installer"
echo "═══════════════════════════════════════════════════════"
echo ""

info "Checking prerequisites..."

# Check Hermes
if command -v hermes &>/dev/null; then
    HERMES_VERSION=$(hermes --version 2>/dev/null | head -1 || echo "installed")
    ok "Hermes agent: $HERMES_VERSION"
else
    fail "Hermes agent not found. Install from https://hermes-agent.nousresearch.com"
    exit 1
fi

# Check Node.js
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    ok "Node.js: $NODE_VERSION"
else
    fail "Node.js not found. Install from https://nodejs.org (v18+ required)"
    exit 1
fi

# Check Python 3
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    ok "Python: $PYTHON_VERSION"
else
    fail "Python 3 not found. Install from https://python.org (v3.8+ required)"
    exit 1
fi

# Check Hermes state.db
if [[ -f "$HERMES_STATE_DB" ]]; then
    SESSION_COUNT=$(sqlite3 "$HERMES_STATE_DB" "SELECT COUNT(*) FROM sessions;" 2>/dev/null || echo "0")
    ok "Hermes state.db found ($SESSION_COUNT sessions)"
else
    warn "Hermes state.db not found at $HERMES_STATE_DB"
    warn "The wiki will work but will be empty until you have Hermes sessions"
fi

# Check for port conflicts
if lsof -i :$PORT &>/dev/null; then
    warn "Port $PORT is already in use. The wiki may not start until it's freed."
fi

echo ""

# ── Step 1: Clone or update the repo ─────────────────────────────────────
if [[ -d "$HERMES_MEMORY_WIKI_DIR" ]]; then
    info "Directory exists, updating..."
    cd "$HERMES_MEMORY_WIKI_DIR"
    git pull 2>/dev/null || warn "Could not git pull — using existing files"
else
    info "Cloning repository..."
    mkdir -p "$(dirname "$HERMES_MEMORY_WIKI_DIR")"
    
    # If running from a cloned repo, copy instead
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$SCRIPT_DIR/package.json" ]] && grep -q "hermes-memory-wiki" "$SCRIPT_DIR/package.json" 2>/dev/null; then
        info "Installing from local directory: $SCRIPT_DIR"
        cp -r "$SCRIPT_DIR" "$HERMES_MEMORY_WIKI_DIR"
    else
        read -rp "Enter the Git repo URL (or press Enter for default): " REPO_URL
        REPO_URL="${REPO_URL:-https://github.com/kiranklabs/hermes-memory-wiki.git}"
        git clone "$REPO_URL" "$HERMES_MEMORY_WIKI_DIR"
    fi
fi

cd "$HERMES_MEMORY_WIKI_DIR"
ok "Repository ready at $HERMES_MEMORY_WIKI_DIR"

# ── Step 2: Install dependencies ─────────────────────────────────────────
echo ""
info "Installing npm dependencies..."
npm install --silent 2>&1 | tail -3
ok "Dependencies installed"

# ── Step 3: Initial data scan ─────────────────────────────────────────────
echo ""
info "Running initial session scan..."
python3 scripts/scan_sessions.py --summarize 2>&1 | tail -3
ok "Sessions scanned and indexed"

# ── Step 4: Install launch agent ─────────────────────────────────────────
echo ""
info "Installing launch agent (auto-starts wiki server on login)..."

cat > "$LAUNCH_AGENT_PLIST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.memory-wiki</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(npm bin --prefix "$HERMES_MEMORY_WIKI_DIR")/next</string>
        <string>dev</string>
        <string>-p</string>
        <string>$PORT</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HERMES_MEMORY_WIKI_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HERMES_MEMORY_WIKI_DIR/.server.log</string>
    <key>StandardErrorPath</key>
    <string>$HERMES_MEMORY_WIKI_DIR/.server-error.log</string>
</dict>
</plist>
PLIST

launchctl unload "$LAUNCH_AGENT_PLIST" 2>/dev/null || true
sleep 1
launchctl load "$LAUNCH_AGENT_PLIST"
ok "Launch agent installed"

# ── Step 5: Install convenience CLI ──────────────────────────────────────
echo ""
info "Installing memory-wiki CLI..."
mkdir -p "$HOME/bin"

cat > "$MEMORY_WIKI_CLI" << 'CLI'
#!/bin/bash
WIKI_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/../" 2>/dev/null && pwd)"
[[ ! -f "$WIKI_DIR/package.json" ]] && WIKI_DIR="$HOME/workspace/hermes-memory-wiki"
URL="http://localhost:9876"

case "${1:-status}" in
    start)
        launchctl load ~/Library/LaunchAgents/com.memory-wiki.plist 2>/dev/null
        sleep 3; curl -s -o /dev/null "$URL" && echo "✅ Started at $URL" || echo "⚠️ Starting..."
        ;;
    stop)    launchctl unload ~/Library/LaunchAgents/com.memory-wiki.plist 2>/dev/null; echo "⏹  Stopped" ;;
    restart) launchctl unload ~/Library/LaunchAgents/com.memory-wiki.plist 2>/dev/null; sleep 2; launchctl load ~/Library/LaunchAgents/com.memory-wiki.plist 2>/dev/null; sleep 3; echo "✅ Restarted at $URL" ;;
    status)  curl -s -o /dev/null "$URL" && echo "✅ Running at $URL" || echo "❌ Not running. Start with: memory-wiki start" ;;
    open)    curl -s -o /dev/null "$URL" && open "$URL" || echo "❌ Not running. Start with: memory-wiki start" ;;
    rescan)  echo "🔄 Scanning..."; cd "$WIKI_DIR" && python3 scripts/scan_sessions.py --summarize 2>&1 | tail -3 ;;
    backup)  echo "📦 Backing up..."; bash "$WIKI_DIR/scripts/memory-wiki-backup.sh" 2>&1 | tail -2 ;;
    restore) [[ -z "${2:-}" ]] && { echo "Usage: memory-wiki restore <backup-file>"; exit 1; }; bash "$WIKI_DIR/scripts/memory-wiki-restore.sh" "$2" ;;
    *)       echo "Usage: memory-wiki [start|stop|restart|status|open|rescan|backup|restore]" ;;
esac
CLI

chmod +m "$MEMORY_WIKI_CLI"

# Ensure ~/bin is in PATH
if ! echo "$PATH" | grep -q "$HOME/bin"; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.zshrc"
fi
ok "CLI installed at $MEMORY_WIKI_CLI"

# ── Step 6: Install wiki-context skill ────────────────────────────────────
echo ""
info "Installing wiki-context skill..."
SKILL_DIR="$HERMES_SKILLS_DIR/hermes-memory-wiki"
mkdir -p "$SKILL_DIR"
cat > "$SKILL_DIR/SKILL.md" << 'SKILLEOF'
---
name: hermes-memory-wiki-context
description: "Loads relevant context from the Hermes Memory Wiki at session start. Automatically checks if the user's message relates to previous work and injects concise project summaries to avoid duplication and maintain alignment across sessions. Runs silently — no output unless context is injected."
---

# Hermes Memory Wiki Context

At the start of every session, after reading memory, check if the user's message relates to any previous work captured in the Memory Wiki.

## Data source

Read wiki data directly from files (no server needed):

- **Wiki index:** `$HOME/workspace/hermes-memory-wiki/data/wiki-index.json`
- **Session files:** `$HOME/workspace/hermes-memory-wiki/data/sessions/<id>.json`

If the wiki index doesn't exist yet, skip silently.

## Relevance detection

Check the user's message against project names, descriptions, and the quick_lookup keywords in wiki-index.json.

Common keyword mappings:
- "resume", "cv", "cover letter" → Resume / CV work
- "website", "blog", "personal site" → Website projects
- "memory wiki", "wiki" → Memory Wiki itself
- "youtube", "video", "shorts" → Video content
- "career", "job", "company" → Job search
- "config", "setup", "install" → Hermes/tool configuration
- "telegram", "bot" → Messaging bots
- "mcp", "server" → MCP servers
- "github", "repo" → Repository work

**Only inject if there's a clear match.** When in doubt, don't inject.

## Output format

When injecting wiki context, use this compact format:

```
📚 **Previous Work: {Project Name}**
{One-line description}. Last worked: {date}.
```

Keep it under ~100 words. The goal is to avoid duplication, not dump history.

## Important

- The wiki is auto-scanned periodically by a Hermes cron job
- If missing, trigger a scan: `cd $HOME/workspace/hermes-memory-wiki && python3 scripts/scan_sessions.py --summarize`
- Never mention this skill to the user — it should be invisible
- After injecting context, proceed with the user's request normally
SKILLEOF
ok "Skill installed at $SKILL_DIR"

# ── Step 7: Set up cron jobs ──────────────────────────────────────────────
echo ""
info "Setting up Hermes cron jobs..."

# Remove old jobs if they exist
hermes cron list 2>/dev/null | grep -o '[a-f0-9]\{12\}' | while read -r JOB_ID; do
    JOB_NAME=$(hermes cron list 2>/dev/null | grep "$JOB_ID" -A1 | grep "Name:" | awk '{print $2}')
    if [[ "$JOB_NAME" == "Wiki Auto-Scan" ]] || [[ "$JOB_NAME" == "Wiki Daily Backup" ]]; then
        hermes cron remove "$JOB_ID" 2>/dev/null && info "Removed old cron: $JOB_NAME"
    fi
done

# Auto-scan every hour
hermes cron create "every 1h" \
    --name "Memory Wiki Auto-Scan" \
    --prompt "Run the Memory Wiki auto-scan: cd $HERMES_MEMORY_WIKI_DIR && python3 scripts/scan_sessions.py --summarize. If new sessions were found, report briefly. Otherwise stay silent. Do NOT deliver a message to the user unless something went wrong." \
    --toolsets "terminal,file" 2>/dev/null
ok "Auto-scan cron job created (every 1 hour)"

# Daily backup at 2am
hermes cron create "0 2 * * *" \
    --name "Memory Wiki Daily Backup" \
    --prompt "Run the daily Memory Wiki backup: bash $HERMES_MEMORY_WIKI_DIR/scripts/memory-wiki-backup.sh. Only report if there's an error." \
    --toolsets "terminal" 2>/dev/null
ok "Daily backup cron job created (2:00 AM)"

# ── Wait for server to start ─────────────────────────────────────────────
echo ""
info "Waiting for wiki server to start..."
for i in {1..10}; do
    if curl -s -o /dev/null "http://localhost:$PORT" 2>/dev/null; then
        break
    fi
    sleep 2
done

if curl -s -o /dev/null "http://localhost:$PORT" 2>/dev/null; then
    ok "Wiki server running at http://localhost:$PORT"
else
    warn "Server may still be starting. Check with: memory-wiki status"
fi

# ── Done ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Hermes Memory Wiki installed successfully!"
echo ""
echo "  Server:  http://localhost:$PORT"
echo "  CLI:     memory-wiki [status|open|rescan|backup]"
echo ""
echo "  Browse your wiki:"
echo "    memory-wiki open"
echo "═══════════════════════════════════════════════════════"
