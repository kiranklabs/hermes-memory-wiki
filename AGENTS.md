# Memory Wiki — Agent Guide

This is the Memory Wiki ecosystem. See `README.md` for full documentation.

## Key facts

- **Wiki server:** `http://localhost:9876` (launch agent: `com.memory-wiki`)
- **Data directory:** `data/` (sessions, index, projects, daily logs)
- **Scanner:** `python3 scripts/scan_sessions.py --summarize`
- **Index generator:** `python3 scripts/generate_index.py`
- **CLI:** `memory-wiki [start|stop|restart|status|open|rescan|backup|restore]`

## When making changes

- Edit source in `src/`, data in `data/`, scripts in `scripts/`
- After changing scanner logic, run: `python3 scripts/scan_sessions.py --summarize`
- After changing the index generator, run: `python3 scripts/generate_index.py`
- The wiki server auto-reloads on file changes (Next.js HMR)
- Run `npm run build` to verify no TypeScript errors

## Data flow

```
Session data → scan_sessions.py → data/sessions/*.json + data/projects.json
                                      ↓
                              generate_index.py → data/wiki-index.json
                                      ↓
                              Wiki context skill reads index at session start
```
