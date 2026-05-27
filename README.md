# 🧠 Hermes Memory Wiki

> A browsable, searchable memory layer for Hermes AI agent conversations — automatically captured, summarized with multi-pass dialectic reasoning, and injected as context into every new session.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Built%20for-Hermes%20Agent-green.svg)](https://hermes-agent.nousresearch.com)
[![Version](https://img.shields.io/badge/version-2.0-blue.svg)](CHANGELOG.md)

## What is it?

Hermes Memory Wiki solves a fundamental problem with AI agents: **every new session starts from scratch**. You repeat context, re-explain your projects, and risk duplicating work. This system changes that.

It's three things working together:

1. **📖 A web wiki** — Browse all past sessions, search conversations, explore projects, and read full transcripts at `http://localhost:9876`
2. **🧠 A context skill with dialectic reasoning** — Automatically loads rich, relevant previous work into every new Hermes session using multi-pass LLM reasoning to capture not just *what* happened but *why* it matters
3. **⚡ An auto-scan pipeline** — Runs every hour to capture new sessions, generate dialectic summaries, classify into projects, and update the wiki

## v2.0 — What's New

The biggest upgrade in v2.0 is **multi-pass dialectic reasoning** for session summaries.

Instead of simple keyword extraction, each session is now analyzed through 3 LLM-powered reasoning passes:

| Pass | What it does |
|------|-------------|
| **Extract** | Identifies what was asked, done, decided, and accomplished |
| **Reason** | Analyzes patterns and preferences across previous sessions in the same project |
| **Synthesize** | Produces a rich context summary optimized for AI assistant injection |

This means when you start a new session saying "let's work on my API project," the injected context captures *preferences* (e.g., "user prefers JWT auth with refresh tokens"), *decisions* (e.g., "using PostgreSQL with migrations"), and *where things left off* (e.g., "next step is adding rate limiting middleware") — not just a flat summary.

```
Hermes conversations
        │
        │  every 1 hour (auto)
        ▼
┌──────────────────────┐
│  Memory Wiki Auto-Scan│  Hermes cron job
│  • Detects new sessions│
│  • 3-pass dialectic    │
│    reasoning (LLM)     │
│  • Classifies projects │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────┐     ┌──────────────────────┐
│   Memory Wiki UI     │     │  Wiki Context Skill   │
│   (localhost:9876)   │     │  (auto-loads per      │
│                      │     │   session)            │
│  • Browse sessions   │     │                       │
│  • Search everything │     │  • Reads dialectic    │
│  • Project grouping  │     │    context from index │
│  • Daily timeline    │     │  • Matches your msg   │
│  • Full transcripts  │     │  • Injects rich       │
└─────────────────────┘     │    context (~150w)    │
           ▲                └──────────────────────┘
           │                          ▲
      You browse                  Every new session
      manually                    gets dialectic context
                                  automatically
```

## Quick Start

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/kiranklabs/hermes-memory-wiki/main/scripts/install.sh | bash
```

### Manual Install

```bash
# Clone the repo
git clone https://github.com/kiranklabs/hermes-memory-wiki.git
cd hermes-memory-wiki

# Run the installer
bash scripts/install.sh
```

The installer will:
1. ✅ Check prerequisites (Hermes, Node.js, Python)
2. ✅ Install npm dependencies
3. ✅ Run initial session scan
4. ✅ Install the launch agent (auto-starts server on login)
5. ✅ Install the `memory-wiki` CLI
6. ✅ Install the wiki-context skill
7. ✅ Set up auto-scan and backup cron jobs

### After Install

```bash
memory-wiki open      # Open the wiki in your browser
memory-wiki status    # Check server status
memory-wiki rescan    # Manually scan new sessions
```

**Browse to: [http://localhost:9876](http://localhost:9876)**

## Features

### 📖 Browsable Session Archive
Every Hermes conversation is captured and presented in a clean, searchable web interface:
- **Session detail pages** with narrative summaries and full transcripts
- **Project grouping** — sessions automatically classified into projects (Website, Resume, Career Research, etc.)
- **Daily timeline** — browse sessions by day
- **Full-text search** across all conversations
- **Dark theme** optimized for long reading sessions

### 🧠 Automatic Context Injection with Dialectic Reasoning
The wiki-context skill runs silently at the start of every new session:
- Reads the compact wiki index (~10KB, fast)
- Matches your message against project names, descriptions, and keywords
- If relevant previous work exists, injects a rich dialectic context summary
- If no match, stays silent — zero token overhead

**Dialectic reasoning** means each session summary is generated by a multi-pass LLM process:
1. **Extract**: What was asked, done, decided, and accomplished
2. **Reason**: What patterns and preferences emerge from this and previous sessions
3. **Synthesize**: A concise context summary optimized for AI assistant injection

This produces far richer context than simple keyword extraction — the injected summary captures not just *what* happened but *why* it matters and *what to remember*.

**Example:**
> **You:** "Let's pick up where we left off on the API project"
>
> **Hermes (automatically):**
> ```
> 📚 Previous Work: Backend API
> Built a REST API with authentication and rate limiting.
> The user prefers JWT-based auth with refresh tokens. Set up the database schema
> using PostgreSQL with migrations. Deployed to production via Docker. Next step
> is adding rate limiting middleware. Last worked: 2026-05-24.
> ```
> Now, what would you like to update?

### ⚡ Auto-Scan Pipeline with Dialectic Reasoning
- **Every 1 hour**: Hermes cron job scans `state.db` for new/changed sessions
- **Multi-pass dialectic summaries**: Each session gets analyzed through 3 LLM reasoning passes (Extract → Reason → Synthesize) that capture what happened, what patterns emerged, and what context matters for future sessions
- **Auto-titles**: Session titles are generated from the first user message
- **Project classification**: Sessions are grouped into meaningful work areas using keyword matching
- **Cross-session reasoning**: Pass 2 uses previous session summaries from the same project to identify patterns and preferences
- **Daily backup**: Full backup tarball created at 2:00 AM, keeps last 10 backups

### 🔧 Zero Maintenance
- **Launch agent** keeps the wiki server running — auto-starts on login, auto-restarts if it crashes
- **Cron jobs** handle scanning and backups automatically
- **CLI commands** for manual control when needed

## Architecture

### Tech Stack
- **Frontend**: Next.js 16+ (App Router), Tailwind CSS 4, TypeScript
- **Data Layer**: JSON files generated from Hermes `state.db` (SQLite)
- **Scanner**: Python 3 script with zero external dependencies (stdlib only)
- **Context**: Hermes skill (SKILL.md) — no server dependency, reads files directly
- **Scheduling**: Hermes cron jobs + macOS launch agent

### Data Flow
```
Hermes state.db (source of truth)
        │
        │  scan_sessions.py (--summarize)
        │  ┌─────────────────────────────────────────┐
        │  │  Pass 1: Extract key facts              │
        │  │  Pass 2: Reason about patterns          │  ← Multi-pass dialectic
        │  │  Pass 3: Synthesize context summary     │     reasoning via LLM
        │  └─────────────────────────────────────────┘
        ▼
data/sessions/<id>.json    ← Full session data + dialectic summary
data/projects.json         ← Project groupings
data/daily_logs.json       ← Daily session groupings
        │
        │  generate_index.py
        ▼
data/wiki-index.json       ← Compact index with dialectic context (skill-consumable)
        │
        ├──→ Wiki UI (Next.js, port 9876)
        └──→ Wiki Context Skill (reads dialectic_context at session start)
```

### File Structure
```
hermes-memory-wiki/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Home page (stats, projects, recent sessions)
│   │   ├── layout.tsx            # Root layout (sidebar + search bar)
│   │   ├── sessions/[id]/page.tsx  # Session detail (summary + transcript)
│   │   ├── daily/[date]/page.tsx   # Daily log (all sessions for a day)
│   │   ├── projects/[name]/page.tsx # Project detail (all sessions in project)
│   │   └── api/search/route.ts     # Search API
│   ├── components/
│   │   ├── Sidebar.tsx           # Tree navigation (projects + timeline)
│   │   └── SearchBar.tsx         # Persistent search bar
│   └── lib/
│       ├── data.ts               # Data loading layer
│       └── format.ts             # Shared formatting utilities
├── scripts/
│   ├── scan_sessions.py          # Main scanner (summaries, titles, classification)
│   ├── generate_index.py         # Wiki index generator
│   ├── memory-wiki-backup.sh     # Backup script
│   ├── memory-wiki-restore.sh    # Restore script
│   ├── rescan.sh                 # Convenience rescan
│   └── install.sh                # One-click installer
├── data/                         # Generated data (auto-scanned)
│   ├── sessions/                 # Individual session JSONs
│   ├── sessions.json             # Session metadata index
│   ├── projects.json             # Project groupings
│   ├── daily_logs.json           # Daily logs
│   └── wiki-index.json           # Compact index for context skill
├── public/                       # Static assets
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── postcss.config.mjs
├── eslint.config.mjs
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Use Cases

### 🔄 Never Repeat Yourself
Start a new session and immediately get context about what you've already done. No more re-explaining your project structure, preferences, or past decisions.

### 📋 Project Continuity
Work on a project across multiple sessions with full awareness of what was accomplished previously. The wiki tracks outcomes, not just conversations.

### 🔍 Search Past Work
Can't remember when you discussed something? Full-text search across all sessions with results showing title, summary, date, and project.

### 📊 Understand Your Patterns
The project classification shows you where you spend your time. Daily logs show your work patterns over time.

### 🔀 Session Recovery
Hermes sessions can be lost or compressed. The wiki preserves the full transcript and narrative summary permanently.

### 🤖 Multi-Agent Alignment
If you use multiple Hermes profiles or agents, the wiki provides a shared memory layer that keeps everyone aligned.

## Best Practices

### Let It Run Automatically
The system is designed to be zero-maintenance. The auto-scan cron runs every hour, the launch agent keeps the server running, and backups happen daily. You don't need to do anything.

### Run Rescan After Big Sessions
If you've had a long, productive session and want it in the wiki immediately:
```bash
memory-wiki rescan
```

### Backup & Restore

**Backups** are created daily at 2:00 AM and stored in `~/memory-wiki-backups/` as timestamped tarballs (e.g., `memory-wiki-backup_20260526_180854.tar.gz`). Each backup is ~10-15MB. Only the last 10 backups are kept.

A backup includes:
- All session data (transcripts, summaries, project classifications)
- Hermes `state.db` (the source of conversation history)
- Launch agent and skill configurations
- Wiki app source code and configs

**To restore** on the same or a new machine:
```bash
memory-wiki restore memory-wiki-backup_20260526_180854.tar.gz
```

The restore script handles everything: installs dependencies, restores data, merges conversation history into the existing `state.db`, reinstalls the launch agent and skill.

Run a manual backup anytime:
```bash
memory-wiki backup
```

### Customize Project Classification
Edit `scripts/scan_sessions.py` → `PROJECTS` list to add your own project categories and keywords. The classifier uses keyword matching against session titles and first user messages.

### Port Conflicts
If port 9876 is already in use, edit the launch agent plist:
```bash
# Change -p 9876 to your desired port in:
~/Library/LaunchAgents/com.memory-wiki.plist
# Then reload:
launchctl unload ~/Library/LaunchAgents/com.memory-wiki.plist
launchctl load ~/Library/LaunchAgents/com.memory-wiki.plist
```

## CLI Reference

```bash
memory-wiki status      # Check if server is running
memory-wiki start       # Start the wiki server
memory-wiki stop        # Stop the wiki server
memory-wiki restart     # Restart the wiki server
memory-wiki open        # Open in browser
memory-wiki rescan      # Manually scan new sessions
memory-wiki backup      # Create backup tarball
memory-wiki restore <f> # Restore from backup file
```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_STATE_DB` | `~/.hermes/state.db` | Path to Hermes state.db |
| `PORT` | `9876` | Wiki server port |

### Hermes Cron Jobs
| Job | Schedule | Purpose |
|-----|----------|---------|
| Memory Wiki Auto-Scan | Every 1 hour | Scans new sessions, generates summaries |
| Memory Wiki Daily Backup | Daily at 2:00 AM | Creates backup tarball |

View all cron jobs:
```bash
hermes cron list
```

### Launch Agent
The wiki server runs as a macOS launch agent (`com.memory-wiki`):
- `RunAtLoad: true` — starts on login
- `KeepAlive: true` — auto-restarts if it crashes

## Requirements

- **macOS** (launch agent support)
- **Hermes Agent** ([install](https://hermes-agent.nousresearch.com))
- **Node.js** v18+ ([install](https://nodejs.org))
- **Python** v3.8+ (stdlib only, no pip packages needed)
- **Git** (for cloning)

## Troubleshooting

**Wiki server not loading:**
```bash
memory-wiki status
memory-wiki restart
# Check logs:
cat ~/workspace/hermes-memory-wiki/.server-error.log
```

**Sessions not appearing:**
```bash
memory-wiki rescan
```

**Context not injecting in new sessions:**
- Ensure `data/wiki-index.json` exists and is recent
- Run `memory-wiki rescan` to regenerate
- Check skill file: `~/.hermes/skills/hermes-memory-wiki/SKILL.md`

**Port 9876 in use:**
```bash
lsof -i :9876
kill <PID>
memory-wiki restart
```

## Contributing

Contributions welcome! Areas of interest:
- Additional project classification keywords
- Enhanced summary generation
- Alternative frontend themes
- Windows/Linux support (currently macOS-only)

## License

[MIT](LICENSE) — use it freely, modify it, share it.
