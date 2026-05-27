#!/bin/bash
# memory-wiki-restore.sh — Restore the Memory Wiki ecosystem from a backup
# Run this on a new machine after installing Hermes
#
# Usage:
#   memory-wiki-restore <backup-file.tar.gz>
#
# Prerequisites:
#   - Hermes agent installed (hermes --version works)
#   - Node.js installed (node --version works)
#   - Git installed

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: memory-wiki-restore <backup-file.tar.gz>"
    echo ""
    echo "Prerequisites:"
    echo "  - Hermes agent:  hermes --version"
    echo "  - Node.js:       node --version"
    echo "  - Git:           git --version"
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check prerequisites
echo "🔍 Checking prerequisites..."
command -v hermes >/dev/null 2>&1 || { echo "❌ Hermes not found. Install from https://hermes-agent.nousresearch.com"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js not found. Install from https://nodejs.org"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ Git not found. Install Xcode Command Tools: xcode-select --install"; exit 1; }
echo "✅ All prerequisites met"

# Extract backup
STAGING=$(mktemp -d)
trap "rm -rf $STAGING" EXIT
echo "📦 Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$STAGING"

# Read metadata
if [[ -f "$STAGING/BACKUPINFO.json" ]]; then
    echo "📋 Backup info:"
    cat "$STAGING/BACKUPINFO.json" | python3 -m json.tool 2>/dev/null || cat "$STAGING/BACKUPINFO.json"
    echo ""
fi

# --- 1. Restore wiki app ---
WIKI_DIR="$HOME/workspace/memory-wiki"
echo "📁 Setting up wiki app at $WIKI_DIR..."
mkdir -p "$WIKI_DIR"

# Copy app source (merge with existing if present)
if [[ -d "$STAGING/wiki-app/src" ]]; then
    cp -r "$STAGING/wiki-app/src" "$WIKI_DIR/"
fi
if [[ -d "$STAGING/wiki-app/scripts" ]]; then
    cp -r "$STAGING/wiki-app/scripts" "$WIKI_DIR/"
fi
if [[ -d "$STAGING/wiki-app/public" ]]; then
    cp -r "$STAGING/wiki-app/public" "$WIKI_DIR/"
fi
for f in package.json package-lock.json tsconfig.json next.config.ts tailwind.config.ts postcss.config.mjs AGENTS.md; do
    [[ -f "$STAGING/wiki-app/$f" ]] && cp "$STAGING/wiki-app/$f" "$WIKI_DIR/"
done

# Install dependencies
echo "📦 Installing dependencies..."
cd "$WIKI_DIR"
if [[ -f package.json ]]; then
    npm install --silent 2>&1 | tail -3
fi
echo "✅ Wiki app ready"

# --- 2. Restore wiki data ---
echo "📋 Restoring wiki data..."
mkdir -p "$WIKI_DIR/data/sessions"
if [[ -d "$STAGING/wiki-data" ]]; then
    cp -r "$STAGING/wiki-data/"* "$WIKI_DIR/data/" 2>/dev/null || true
fi
SESSION_COUNT=$(ls "$WIKI_DIR/data/sessions/"*.json 2>/dev/null | wc -l)
echo "✅ $SESSION_COUNT sessions restored"

# --- 3. Restore Hermes state.db ---
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
if [[ -f "$STAGING/state.db" ]]; then
    echo "🗄️  Restoring Hermes state.db..."
    mkdir -p "$HERMES_HOME"
    
    if [[ -f "$HERMES_HOME/state.db" ]]; then
        # Merge: restore sessions table from backup
        # Use sqlite3 to copy sessions + messages from backup into existing DB
        BACKUP_DB="$STAGING/state.db"
        EXISTING_DB="$HERMES_HOME/state.db"
        
        # Get sessions from backup
        BACKUP_SESSIONS=$(sqlite3 "$BACKUP_DB" "SELECT COUNT(*) FROM sessions;" 2>/dev/null || echo "0")
        
        # Copy sessions and messages from backup into existing DB
        # Use INSERT OR IGNORE to avoid duplicates
        sqlite3 "$EXISTING_DB" << SQL
ATTACH DATABASE '$BACKUP_DB' AS backup;
INSERT OR IGNORE INTO main.sessions SELECT * FROM backup.sessions;
INSERT OR IGNORE INTO main.messages SELECT * FROM backup.messages;
DETACH DATABASE backup;
SQL
        
        TOTAL=$(sqlite3 "$EXISTING_DB" "SELECT COUNT(*) FROM sessions;")
        echo "✅ State.db merged: $BACKUP_SESSIONS sessions from backup, $TOTAL total"
    else
        # Fresh install — just copy
        cp "$STAGING/state.db" "$HERMES_HOME/state.db"
        echo "✅ State.db restored fresh"
    fi
fi

# --- 4. Restore wiki-context skill ---
echo "🧩 Installing wiki-context skill..."
SKILL_DIR="$HERMES_HOME/skills/wiki-context"
mkdir -p "$SKILL_DIR"
if [[ -d "$STAGING/skills/wiki-context" ]]; then
    cp -r "$STAGING/skills/wiki-context/"* "$SKILL_DIR/"
    echo "✅ Skill installed at $SKILL_DIR"
fi

# --- 5. Install convenience CLI ---
echo "🔧 Installing memory-wiki CLI..."
mkdir -p "$HOME/bin"
cp "$STAGING/memory-wiki" "$HOME/bin/memory-wiki"
chmod +x "$HOME/bin/memory-wiki"

# Ensure ~/bin is in PATH
if ! echo "$PATH" | grep -q "$HOME/bin"; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.zshrc"
    echo "✅ Added ~/bin to PATH (restart terminal or: source ~/.zshrc)"
fi

# --- 6. Install launch agent ---
echo "🚀 Installing launch agent..."
mkdir -p "$HOME/Library/LaunchAgents"

PLIST_PATH="$HOME/Library/LaunchAgents/com.memory-wiki.plist"

# Copy and update the plist to match current machine
cp "$STAGING/launch-agent.plist" "$PLIST_PATH"
CURRENT_USER=$(whoami)
CURRENT_HOME="$HOME"
/usr/libexec/PlistBuddy -c "Set :WorkingDirectory $CURRENT_HOME/workspace/memory-wiki" "$PLIST_PATH" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:0 /usr/bin/python3" "$PLIST_PATH" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:2 $CURRENT_HOME/workspace/memory-wiki/node_modules/.bin/next" "$PLIST_PATH" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :StandardOutPath $CURRENT_HOME/workspace/memory-wiki/.server.log" "$PLIST_PATH" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath $CURRENT_HOME/workspace/memory-wiki/.server-error.log" "$PLIST_PATH" 2>/dev/null || true

# Load it
launchctl unload "$PLIST_PATH" 2>/dev/null || true
sleep 1
launchctl load "$PLIST_PATH" 2>/dev/null
echo "✅ Launch agent installed"

# --- 7. Create cron job ---
echo "⏰ Setting up auto-scan cron job..."
# Note: Hermes cron needs to be set up manually or via hermes CLI
# We'll create a wrapper that the user can run
cat > "$WIKI_DIR/scripts/setup-cron.sh" << 'CRONEOF'
#!/bin/bash
# Run this to set up the Wiki Auto-Scan cron job in Hermes
echo "Setting up Wiki Auto-Scan cron job..."
hermes cron create "every 1h" --name "Wiki Auto-Scan" --prompt "Run the Memory Wiki auto-scan: cd $HOME/workspace/memory-wiki && python3 scripts/scan_sessions.py --summarize. If new sessions were found, report briefly. Otherwise stay silent. Do NOT deliver a message to the user unless something went wrong." --toolsets "terminal,file"
CRONEOF
chmod +x "$WIKI_DIR/scripts/setup-cron.sh"
echo "⚠️  Run $WIKI_DIR/scripts/setup-cron.sh to create the Hermes cron job"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "✅ Memory Wiki ecosystem restored!"
echo ""
echo "Next steps:"
echo "  1. Restart terminal (or: source ~/.zshrc)"
echo "  2. Run: $WIKI_DIR/scripts/setup-cron.sh"
echo "  3. Verify: memory-wiki status"
echo "  4. Open:   memory-wiki open"
echo ""
echo "Wiki URL: http://localhost:9876"
echo "═══════════════════════════════════════════════════════"