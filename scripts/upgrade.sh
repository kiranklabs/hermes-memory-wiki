#!/bin/bash
# upgrade.sh — Pull the latest Hermes Memory Wiki from GitHub
# Usage: bash scripts/upgrade.sh

set -euo pipefail

WIKI_DIR="$HOME/workspace/hermes-memory-wiki"

if [[ ! -d "$WIKI_DIR/.git" ]]; then
    echo "❌ Not a git repo. Reinstall with: bash scripts/install.sh"
    exit 1
fi

cd "$WIKI_DIR"

# Check for local changes
if ! git diff --quiet 2>/dev/null; then
    echo "⚠️  You have local changes. Upgrading will overwrite them."
    read -rp "Continue? [y/N] " CONFIRM
    if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
        echo "Aborted. Commit your changes first, then upgrade."
        exit 0
    fi
    git stash 2>/dev/null || true
fi

echo "⬆️  Pulling latest from GitHub..."
git pull 2>&1

# Reinstall dependencies if package.json changed
if git diff HEAD@{1} --name-only 2>/dev/null | grep -q "package.json"; then
    echo "📦 Installing updated dependencies..."
    npm install --silent 2>&1 | tail -2
fi

echo ""
echo "✅ Upgraded successfully!"
echo ""
echo "Restart the wiki server:"
echo "  memory-wiki restart"
