#!/bin/bash
# memory-wiki-backup.sh — Backup the full Memory Wiki ecosystem
# Creates a self-contained tarball that can be restored on another machine
#
# Usage:
#   memory-wiki-backup              # backup to ~/memory-wiki-backups/
#   memory-wiki-backup ~/Dropbox/   # backup to custom location
#   memory-wiki-backup --auto       # auto mode (for cron, no output unless error)

set -euo pipefail

BACKUP_DIR="${1:-$HOME/memory-wiki-backups}"
AUTO_MODE=false
if [[ "${1:-}" == "--auto" ]]; then AUTO_MODE=true; fi

WIKI_DIR="${WIKI_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DB="${HERMES_STATE_DB:-$HOME/.hermes/state.db}"
SKILL_DIR="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}/wiki-context"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.memory-wiki.plist"
MEMORY_WIKI_CLI="$(dirname "$0")/memory-wiki"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/memory-wiki-backup_$TIMESTAMP.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

[[ "$AUTO_MODE" == false ]] && echo "📦 Backing up Memory Wiki ecosystem..."

# Create a staging area
STAGING=$(mktemp -d)
trap "rm -rf $STAGING" EXIT

# 1. Wiki data (sessions, index, projects) — the core
mkdir -p "$STAGING/wiki-data"
cp -r "$WIKI_DIR/data/"* "$STAGING/wiki-data/" 2>/dev/null || true

# 2. Hermes state.db — the source of truth
if [[ -f "$STATE_DB" ]]; then
    # Use SQLite backup for consistency
    sqlite3 "$STATE_DB" ".backup '$STAGING/state.db'"
    [[ "$AUTO_MODE" == false ]] && echo "  ✅ state.db ($(sqlite3 "$STATE_DB" "SELECT COUNT(*) FROM sessions;") sessions)"
fi

# 3. Wiki context skill
mkdir -p "$STAGING/skills/wiki-context"
cp -r "$SKILL_DIR/"* "$STAGING/skills/wiki-context/" 2>/dev/null || true

# 4. Launch agent plist
cp "$LAUNCH_AGENT" "$STAGING/launch-agent.plist" 2>/dev/null || true

# 5. Convenience CLI command
cp "$MEMORY_WIKI_CLI" "$STAGING/memory-wiki" 2>/dev/null || true

# 6. Wiki app source (without node_modules — those are reinstalled)
mkdir -p "$STAGING/wiki-app"
cp -r "$WIKI_DIR/src" "$STAGING/wiki-app/"
cp -r "$WIKI_DIR/scripts" "$STAGING/wiki-app/"
cp -r "$WIKI_DIR/public" "$STAGING/wiki-app/" 2>/dev/null || true
cp "$WIKI_DIR/package.json" "$STAGING/wiki-app/"
cp "$WIKI_DIR/package-lock.json" "$STAGING/wiki-app/" 2>/dev/null || true
cp "$WIKI_DIR/tsconfig.json" "$STAGING/wiki-app/" 2>/dev/null || true
cp "$WIKI_DIR/next.config.ts" "$STAGING/wiki-app/" 2>/dev/null || true
cp "$WIKI_DIR/tailwind.config.ts" "$STAGING/wiki-app/" 2>/dev/null || true
cp "$WIKI_DIR/postcss.config.mjs" "$STAGING/wiki-app/" 2>/dev/null || true
cp "$WIKI_DIR/AGENTS.md" "$STAGING/wiki-app/" 2>/dev/null || true

# 7. Metadata
cat > "$STAGING/BACKUPINFO.json" << EOF
{
    "version": "1.0",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "wiki_dir": "$WIKI_DIR",
    "hermes_home": "$HOME/.hermes",
    "sessions_backed_up": $(sqlite3 "$STATE_DB" "SELECT COUNT(*) FROM sessions;" 2>/dev/null || echo "0"),
    "port": 9876
}
EOF

# Create the tarball
tar -czf "$BACKUP_FILE" -C "$STAGING" .

# Keep only last 10 backups
cd "$BACKUP_DIR"
ls -t memory-wiki-backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
[[ "$AUTO_MODE" == false ]] && echo "✅ Backup saved: $BACKUP_FILE ($SIZE)"
[[ "$AUTO_MODE" == false ]] && echo "   Backups kept: $(ls memory-wiki-backup_*.tar.gz 2>/dev/null | wc -l)"
