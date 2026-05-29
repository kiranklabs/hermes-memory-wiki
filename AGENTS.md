# Hermes Memory Wiki — Agent Guide

This is the Hermes Memory Wiki ecosystem. See `README.md` for full documentation.

## Key facts

- **Wiki server:** `http://localhost:9876` (launch agent: `com.memory-wiki`)
- **Data directory:** `data/` (sessions, index, projects, daily logs, facts, decisions)
- **Scanner:** `python3 scripts/scan_sessions.py` (v2.5 — LLM-only, parallel, incremental)
- **Index generator:** `python3 scripts/generate_index.py`
- **Rebuild utility:** `python3 scripts/rebuild_data.py` (rebuilds ALL index files from session data)
- **CLI:** `memory-wiki [start|stop|restart|status|open|rescan|upgrade|backup|restore|uninstall]`
- **Auto-scan:** Hermes cron job every 1 hour
- **Daily backup:** Hermes cron job at 2:00 AM → `~/memory-wiki-backups/`
- **Context skill:** `~/.hermes/skills/hermes-memory-wiki/SKILL.md`

## When making changes

- Edit source in `src/`, data in `data/`, scripts in `scripts/`
- After changing scanner logic, run: `python3 scripts/scan_sessions.py`
- After changing data files, run: `python3 scripts/rebuild_data.py`
- The wiki server auto-reloads on file changes (Next.js HMR)
- Run `npm run build` to verify no TypeScript errors

## Data flow

```
Hermes state.db (source of truth)
        │
        │  scan_sessions.py  (every 1 hour, automatic)
        │  → LLM summary + title + facts + decisions per session
        │  → parallel processing (3 workers)
        │  → incremental (only new sessions)
        ▼
data/sessions/<id>.json    ← Full session data + summary
data/facts.json            ← Deduplicated facts (5 categories, supersedence)
data/decisions.json        ← User decisions (supersedence trail)
data/cron-jobs.json        ← Cron sessions (categorized separately)
        │
        │  rebuild_data.py  (runs after scan)
        ▼
data/sessions.json         ← Session metadata index
data/projects.json         ← Project groupings
data/daily_logs.json       ← Daily session groupings
data/wiki-index.json       ← Compact index for context injection
        │
        ├──→ Wiki UI (Next.js, localhost:9876)
        │       ├─ /           home: stats, projects, recent sessions
        │       ├─ /sessions   narrative summary + full transcript
        │       ├─ /projects   all sessions in a project
        │       ├─ /daily      sessions grouped by day
        │       ├─ /facts      browse facts by category
        │       └─ /decisions  browse decisions with history
        │
        └──→ Context Skill (auto-loads at session start)
               ├─ Reads wiki-index.json (~15KB)
               ├─ Matches message against projects/keywords
               ├─ Injects facts + decisions + recent work
               └─ Stays silent if no match (zero token cost)
```

## Public repo sanitization

When syncing from private to public repo, see `~/.hermes/skills/devops/open-source-release/SKILL.md` and `references/v2-leak-vectors.md` for the complete sanitization checklist. Key rules:
- Scan ALL file types: `.py`, `.ts`, `.tsx`, `.sh`, `.md`
- Check regex patterns in `.py` files (personal names can hide in regex)
- Check UI strings in `.tsx` files (personal names can hide in JSX)
- `sync-public.sh` must NEVER be committed to public repo (it's in `.gitignore`)
- Session data files in `data/sessions/` must NEVER be committed (use `.gitkeep`)
- Always do a final grep sweep after sync
