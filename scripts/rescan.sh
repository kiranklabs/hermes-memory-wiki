#!/bin/bash
# rescan.sh — Re-run the session scanner to refresh data (with summaries + wiki index)
cd "$(dirname "$0")"
python3 scripts/scan_sessions.py --summarize
echo "Data refreshed at $(date)"
