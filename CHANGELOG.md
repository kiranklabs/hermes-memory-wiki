# Changelog

## v2.1 - Scanner Data Quality Fix

### Fixes

- **Session ballooning prevented**: Scanner now filters out cron sessions (automated noise), sessions with fewer than 3 messages (not meaningful), and scanner self-sessions (dialectic pass outputs being treated as conversations)
- **Memory Wiki project keywords tightened**: Overly broad keywords like "session scanner", "session data", "browsable record" were causing nearly all sessions to be classified as "Memory Wiki". Now uses specific keywords: "memory-wiki", "scan_sessions", "memory wiki site", "memory wiki server", "memory wiki ecosystem"
- **Real-world impact**: Prevents the wiki from accumulating 400+ phantom sessions (was 414, now filtered to ~28 meaningful sessions)
- **Added `memory-wiki upgrade` command**: Users can pull the latest scanner and scripts from GitHub without re-running the full installer

---

## v2.0 - Multi-Pass Dialectic Reasoning

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
