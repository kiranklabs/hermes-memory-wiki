# Changelog

## v2.5 — Facts, Decisions & Cron Jobs

### New Features

- **Facts layer** (`facts.json`): Deduplicated factual statements extracted from session summaries, categorized as environment, preferences, tools, conventions, and constraints. Facts are overwritten (not appended) when they change — old facts are superseded, never deleted.
- **Decisions layer** (`decisions.json`): User decisions extracted from session summaries with full supersedence trail. A decision made today can supersede one from last month — the old choice is kept but marked as replaced, so it never "sneaks back in."
- **Separate Cron Jobs section**: Cron sessions (auto-scan, backup, priority check) are now classified separately and displayed in their own sidebar section — not mixed into project categories.
- **Facts & Decisions pages**: New browseable pages at `/facts` and `/decisions` showing all extracted facts and decisions, grouped by category. Pages render dynamically (not stale-cached) so data is always fresh.
- **`rebuild_data.py` utility**: Safely rebuilds all index files (sessions, projects, daily logs, facts, decisions, wiki index) from session data. Run after every scan to guarantee consistency.

### Changed

- **Scanner v3.0 rewrite**: Removed all lightweight extraction. Every session now gets a proper LLM-generated narrative summary, auto-generated title, and structured fact/decision extraction — all in a single `hermes -z` call per session.
- **Parallel LLM processing**: Scanner uses `ThreadPoolExecutor(max_workers=3)` to process 3 sessions concurrently, reducing scan time by ~3x.
- **Incremental scanning**: Sessions that already have summaries are skipped on re-scan. Only new sessions get LLM calls, making hourly cron runs fast.
- **Date filter**: Scanner only processes sessions from the last 7 days by default (configurable via `days_back` parameter).
- **Session page shows narrative summary**: Removed bulleted structure (what was asked/done/decisions/tools). Now shows a clean LLM-generated narrative summary paragraph.
- **Sidebar**: All collapsible sections (Projects, Timeline, Cron Jobs) are closed by default. Cron Jobs section moved to the bottom of the sidebar. Title renamed to "Hermes Memory Wiki".

### UI Changes

- Sidebar order: Overview → Facts → Decisions → Projects → Timeline → Cron Jobs (last)
- Facts and decisions pages are server-rendered on every request (dynamic) — no stale cache
- Home page title: "Memory Wiki" → "Hermes Memory Wiki"

### Removed

- `--summarize` flag from scanner: LLM summarization is always enabled now (it was the only thing that produced good results)
- Lightweight extraction layer: Bulleted summaries, pattern-based fact extraction — all replaced by LLM-generated narrative summaries with structured fact/decision extraction
- Em-dashes in scanner code (replaced with hyphens to avoid encoding issues)

### Performance

- Scan time for ~100 new sessions: ~4-5 minutes (down from ~10+ minutes) thanks to parallel processing
- Incremental scans (hourly cron): Only new sessions processed, typically under 1 minute
- Facts/decisions pages: Zero token cost in context injection — pre-extracted, compact JSON files

---

## v2.1 — Scanner Data Quality Fix

### Fixes

- **Session ballooning prevented**: Scanner now filters out cron sessions (automated noise), sessions with fewer than 3 messages (not meaningful), and scanner self-sessions (dialectic pass outputs being treated as conversations)
- **Memory Wiki project keywords tightened**: Overly broad keywords like "session scanner", "session data", "browsable record" were causing nearly all sessions to be classified as "Memory Wiki". Now uses specific keywords: "memory-wiki", "scan_sessions", "memory wiki site", "memory wiki server", "memory wiki ecosystem"
- **Real-world impact**: Prevents the wiki from accumulating 400+ phantom sessions (was 414, now filtered to ~28 meaningful sessions)
- **Added `memory-wiki upgrade` command**: Users can pull the latest scanner and scripts from GitHub without re-running the full installer

---

## v2.0 — Multi-Pass Dialectic Reasoning

### New Features

- **Multi-pass dialectic reasoning for session summaries**: Each session is now analyzed through 3 LLM-powered reasoning passes:
  - **Pass 1 — Extract**: Identifies what was asked, done, decided, and accomplished
  - **Pass 2 — Reason**: Analyzes patterns and preferences across previous sessions in the same project
  - **Pass 3 — Synthesize**: Produces a rich context summary optimized for AI assistant injection
- **Diploads dialectic context to wiki index** for use by the context skill
- **Single LLM call per session**: All 3 reasoning passes run in one `hermes -z` call for performance
- **Cross-session reasoning**: Pass 2 uses previous session summaries from the same project to identify user preferences and patterns

### Changed

- Scanner now generates dialectic summaries instead of simple heuristic narrative summaries
- Wiki context skill prefers `dialectic_context` (Pass 3 output) over basic `summary` for injection
- Project "Resume System" renamed to "Documents & Writing" with broader keywords
- Project "YouTube & Video" keywords cleaned (removed specific project references)
- Project "GitHub & Repo Management" keywords cleaned (removed specific project references)
- Updated data flow diagram to show 3-pass reasoning pipeline

### Performance

- Scanner processes sessions sequentially with single LLM call per session
- Full scan of ~90 sessions takes approximately 8-10 minutes
- Falls back to heuristic summary if `hermes -z` is unavailable

---

## v1.0 — Initial Release

- Browsable web wiki for Hermes conversation history
- Auto-scan pipeline with hourly cron jobs
- Daily backups at 2:00 AM
- Project classification with keyword matching
- Context injection via Hermes skill
- One-click install script
- Backup/restore scripts
- CLI commands for server management
