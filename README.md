# 🧠 Hermes Memory Wiki

> **Never repeat yourself to your AI agent.** Hermes Memory Wiki gives your AI assistant a persistent memory — automatically capturing, organizing, and injecting context from every conversation into every new session.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Built%20for-Hermes%20Agent-green.svg)](https://hermes-agent.nousresearch.com)
[![Version](https://img.shields.io/badge/version-2.5-blue.svg)](CHANGELOG.md)

---

## Why This Exists

Here's the problem: **every new Hermes session starts from scratch.** You re-explain your project structure. You re-state your preferences. You risk duplicating work you already did last week. It's like talking to someone with amnesia every single day.

Hermes Memory Wiki solves this by giving your AI a **persistent, searchable memory layer** that automatically:

1. **📖 Captures** — Every Hermes conversation is scanned, summarized with an LLM, and stored in a browsable web wiki
2. **🧠 Remembers** — Facts, decisions, and preferences are extracted and injected into new sessions automatically
3. **⚡ Runs itself** — Hourly scans, daily backups, zero maintenance

---

## What's New in v2.5

### 🏷️ Facts Layer — Your Agent Learns What's True

The scanner now extracts **deduplicated factual statements** from every conversation and stores them in `facts.json`:

- **Environment** — "User runs macOS, deploys via Vercel"
- **Tools** — "Uses Next.js, Tailwind, Python, Docker"
- **Preferences** — "Prefers concise responses, dark theme, branch/PR workflow"
- **Constraints** — "Port 9876, avoids common ports 3000-8080"

**Key benefit:** Facts are **overwritten, not appended**. When something changes (e.g., switching from PostgreSQL to SQLite), the old fact is superseded. Your agent always knows the current truth — not a contradictory history.

### ⚖️ Decisions Layer — Your Agent Knows What You Decided

User decisions are extracted and stored in `decisions.json` with a **full supersedence trail**:

```
✅ Active:   "Use JWT with refresh tokens for API auth" (May 24)
↩️ Superseded: "Use session-based auth with cookies" (May 20)
            Replaced by fact_042 in session 20260524_153000
```

**Key benefit:** Old choices are never deleted — they're **superseded with a trail**. This prevents the AI from "forgetting" what you decided last week and suggesting something you already rejected.

### ⚙️ Cron Jobs — Separated From Your Work

Auto-generated sessions (hourly scans, daily backups, priority check-ins) are now **classified separately** in their own sidebar section. They no longer pollute your project categories.

### 📄 New: Facts & Decisions Pages

Browse all extracted facts and decisions at `/facts` and `/decisions` — grouped by category, with supersedence history. Pages render dynamically so data is always fresh.

### 🔄 Scanner v2.5 — Faster & Smarter

- **LLM-only summarization** — Every session gets a rich narrative summary, auto-generated title, and structured fact/decision extraction (single `hermes -z` call)
- **Parallel processing** — 3 concurrent workers reduce scan time by ~3x
- **Incremental scanning** — Already-summarized sessions are skipped; only new sessions get LLM calls
- **Date filter** — Only scans sessions from the last 7 days by default

---

## End-to-End Example: A Day With Hermes Memory Wiki

Let's walk through how this works in practice.

### Setup (One-Time)
```bash
git clone https://github.com/kiranklabs/hermes-memory-wiki.git
cd hermes-memory-wiki
bash scripts/install.sh
# → Installs everything, runs initial scan, starts the wiki server
```

### Session 1: Building a Web App

```
You: "I want to build a personal portfolio website.
      Use Next.js 15, Tailwind CSS, deploy on Vercel.
      I prefer dark theme with emerald accent colors."

Hermes: "Got it. I'll set up Next.js 15 with Tailwind CSS v4.
         Creating project at ~/workspace/portfolio-site..."
         [Works for 2 hours, sets up CI/CD, deploys to Vercel]
```

**Behind the scenes:** The scanner generates a narrative summary:
> *"User decided to build a personal portfolio website using Next.js 15 and Tailwind CSS v4. Project deployed to Vercel. User prefers dark theme with emerald accent colors (#10b981). Site structure: Home, About, Projects, Blog sections."*

And extracts:
- **Facts:** `environment: Vercel deployment`, `tools: Next.js 15, Tailwind CSS v4`, `preferences: dark theme, emerald accent`
- **Decisions:** `"Use Next.js 15 + Tailwind CSS for portfolio site"`, `"Deploy on Vercel"`

### Session 2: Continuing Work (Next Day)

```
You: "Let's continue working on my portfolio."

Hermes: "📚 Previous Work: Personal Website
         Building a portfolio site with Next.js 15, Tailwind CSS, deployed to Vercel.
         Uses dark theme with emerald accent. Structure: Home, About, Projects, Blog.
         Last worked: yesterday, 21:00.
         
         What would you like to work on?"
```

**No re-explaining.** Hermes knows the stack, the deployment target, the design preferences, and where things left off. The injected context is ~100 words — rich but concise.

### Session 3: Changing Direction

```
You: "Actually, let me switch from Next.js to Astro.
      I want better performance and less JavaScript."

Hermes: "Got it, switching from Next.js to Astro.
         I know your site uses Tailwind CSS and deploys to Vercel — 
         I'll keep that intact while migrating the framework."
```

Behind the scenes, the new decision supersedes the old one:
- ✅ **Active:** `"Switch portfolio from Next.js to Astro for better performance"` (today)
- ↩️ **Superseded:** `"Use Next.js 15 + Tailwind CSS for portfolio site"` (yesterday)

The fact layer gets updated:
- ✅ **Active:** `tools: Astro, Tailwind CSS v4`
- ↩️ **Superseded:** `tools: Next.js 15, Tailwind CSS v4`

### Session 4: Browsing the Wiki

```
You: "What decisions have I made about authentication?"

[Open wiki at http://localhost:9876/decisions]
→ Shows all auth-related decisions with dates and supersedence trail

You: "What tools do I typically use?"

[Open wiki at http://localhost:9876/facts]
→ Shows categorized facts: environment, tools, preferences, conventions, constraints
```

---

## Architecture

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | Next.js 15 (App Router), Tailwind CSS 4, TypeScript | Fast, modern, zero-config |
| **Data Layer** | JSON files from Hermes `state.db` (SQLite) | Zero dependencies, human-readable, git-friendly |
| **Scanner** | Python 3 (stdlib only) | No pip packages, works out of the box |
| **Context** | Hermes skill (SKILL.md) | Reads files directly — no server needed |
| **Scheduling** | Hermes cron jobs + macOS launch agent | Auto-scan every hour, daily backups |

### Data Flow

```
Hermes state.db (source of truth)
        │
        │  scan_sessions.py  (every 1 hour, automatic)
        │  ┌─────────────────────────────────────────────┐
        │  │  1. Collect new/modified sessions           │
        │  │  2. LLM summarizes each session             │
        │  │     → narrative summary + auto-title         │
        │  │     → extract facts (environment, tools,     │
        │  │       preferences, conventions, constraints) │
        │  │     → extract decisions                      │
        │  │  3. Classify into projects / cron jobs       │
        │  │  4. Write individual session files            │
        │  └─────────────────────────────────────────────┘
        ▼
data/sessions/<id>.json    ← Full session data + summary
data/projects.json         ← Project groupings (auto-classified)
data/daily_logs.json       ← Sessions grouped by day
data/cron-jobs.json        ← Cron job sessions (categorized separately)
data/facts.json            ← Deduplicated facts (5 categories, supersedence)
data/decisions.json        ← User decisions (supersedence trail)
        │
        │  rebuild_data.py  (runs after every scan)
        ▼
data/wiki-index.json       ← Compact index for context injection (~15KB)
        │
        ├──→ 📖 Wiki UI (Next.js, localhost:9876)
        │       ├─ Home: stats, projects, recent sessions
        │       ├─ Sessions: narrative summary + full transcript
        │       ├─ Projects: all sessions in a project
        │       ├─ Timeline: sessions grouped by day
        │       ├─ Facts: browse facts by category
        │       └─ Decisions: browse decisions with history
        │
        └──→ 🧠 Context Skill (auto-loads at session start)
               ├─ Reads wiki-index.json (~15KB, fast)
               ├─ Matches message against projects/keywords
               ├─ If relevant: injects facts + decisions + recent work
               └─ If no match: stays silent (zero token cost)
```

### File Structure

```
hermes-memory-wiki/
├── src/
│   ├── app/
│   │   ├── page.tsx                  # Home: stats, projects, recent sessions
│   │   ├── layout.tsx                # Root: sidebar + search bar
│   │   ├── sessions/[id]/page.tsx    # Session: narrative summary + transcript
│   │   ├── projects/[name]/page.tsx  # Project: all sessions in project
│   │   ├── daily/[date]/page.tsx     # Daily: sessions for that day
│   │   ├── facts/page.tsx            # Facts: browse by category
│   │   ├── decisions/page.tsx        # Decisions: browse with history
│   │   └── api/search/route.ts       # Full-text search API
│   ├── components/
│   │   ├── Sidebar.tsx               # Tree nav: projects, timeline, cron
│   │   └── SearchBar.tsx             # Persistent search
│   └── lib/
│       ├── data.ts                   # Data loading (projects, facts, decisions, cron)
│       └── format.ts                 # Formatting utilities
├── scripts/
│   ├── scan_sessions.py              # v2.5: LLM summaries, facts, decisions
│   ├── rebuild_data.py               # Rebuild all index files from session data
│   ├── generate_index.py             # Wiki index generator
│   ├── install.sh                    # One-click installer
│   ├── uninstall.sh                  # Complete uninstaller
│   ├── memory-wiki-backup.sh         # Daily backup script
│   ├── memory-wiki-restore.sh        # Restore from backup
│   └── rescan.sh                     # Manual rescan convenience
├── data/                             # Generated locally (gitignored)
│   ├── sessions/                     # Individual session files
│   ├── sessions.json                 # Session index
│   ├── projects.json                 # Project groupings
│   ├── daily_logs.json               # Daily logs
│   ├── cron-jobs.json                # Cron job sessions
│   ├── facts.json                    # Facts layer
│   ├── decisions.json                # Decisions layer
│   └── wiki-index.json               # Compact context injection index
├── public/                           # Static assets
└── ...
```

## Quick Start

### One-Line Install
```bash
curl -fsSL https://raw.githubusercontent.com/kiranklabs/hermes-memory-wiki/main/scripts/install.sh | bash
```

### Manual Install
```bash
git clone https://github.com/kiranklabs/hermes-memory-wiki.git
cd hermes-memory-wiki
bash scripts/install.sh
```

The installer handles everything:
1. ✅ Checks prerequisites (Hermes, Node.js, Python)
2. ✅ Installs npm dependencies
3. ✅ Runs initial session scan (summarizes all existing Hermes sessions)
4. ✅ Installs the launch agent (auto-starts on login, auto-restarts if crashed)
5. ✅ Installs the `memory-wiki` CLI
6. ✅ Installs the wiki-context skill
7. ✅ Sets up auto-scan (hourly) and daily backup (2 AM) cron jobs

### After Install
```bash
memory-wiki open      # Open wiki in browser
memory-wiki status    # Check server status
memory-wiki rescan    # Manually trigger a scan
```

**Browse to: [http://localhost:9876](http://localhost:9876)**

## CLI Reference

```bash
memory-wiki status      # Check if server is running
memory-wiki start       # Start the wiki server
memory-wiki stop        # Stop the wiki server
memory-wiki restart     # Restart the wiki server
memory-wiki open        # Open in browser
memory-wiki rescan      # Manually scan new sessions
memory-wiki upgrade     # Pull latest scripts from GitHub
memory-wiki backup      # Create backup tarball
memory-wiki restore <f> # Restore from backup file
memory-wiki uninstall   # Remove everything (or: bash scripts/uninstall.sh)
```

## How Context Injection Works

The magic happens through a Hermes skill that runs silently at the start of every new session.

### Step 1: Skill Reads Index
The skill reads `data/wiki-index.json` (~15KB) — a compact index of projects, sessions, facts, and decisions.

### Step 2: Relevance Detection
It matches your message against project names, descriptions, and keywords:
- "resume" / "cv" / "cover letter" → Documents & Writing
- "website" / "blog" / "portfolio" → Website projects
- "memory wiki" / "wiki" → Memory Wiki itself
- "youtube" / "video" / "shorts" → Video content
- "career" / "job" / "company" → Job search
- "config" / "setup" / "install" → Hermes/tool configuration
- "telegram" / "bot" → Messaging bots
- "github" / "repo" → Repository work

### Step 3: Injection (Only If Relevant)

**If there's a match**, injects a compact context block (~100-150 words):

```
📚 Previous Work: Personal Website
Building a portfolio site with Next.js 15, Tailwind CSS, deployed to Vercel.
Dark theme with emerald accent. Structure: Home, About, Projects, Blog.
Key facts: Vercel deployment, prefers concise API responses.
Decision: Use Astro instead of Next.js for better performance (May 28).
Last worked: 2026-05-28.
```

**If no match**, stays silent — zero token overhead.

### Step 4: You Get Continuity
Hermes now knows what you built, what you decided, and where things left off. No re-explaining. No contradictory suggestions.

## Features Deep-Dive

### 📖 Browsable Session Archive
- **Session detail pages** with AI-generated narrative summaries and full transcripts
- **Project grouping** — sessions auto-classified into meaningful work areas
- **Daily timeline** — browse sessions by day
- **Facts & Decisions pages** — browse extracted knowledge
- **Full-text search** across all conversations
- **Dark theme** optimized for long reading sessions

### 🧠 Three-Layer Memory

| Layer | File | Update | Supersedence |
|-------|------|--------|--------------|
| **Facts** | `facts.json` | Extracted from session summaries | Old facts superseded (not deleted) |
| **Decisions** | `decisions.json` | Extracted from user choices | Full trail: what replaced what and when |
| **Summaries** | `wiki-index.json` | LLM narrative per session | Auto-title + project classification |

### ⚡ Auto-Scan Pipeline
- **Every hour**: Hermes cron job scans for new/changed sessions
- **LLM summarization**: Single `hermes -z` call per session with parallel workers
- **Incremental**: Only new sessions processed; already-summarized ones skipped
- **Cron separation**: Auto-scan sessions tracked separately, not mixed with real work
- **Daily backup**: Full backup at 2 AM, keeps last 10 backups

### 🔧 Zero Maintenance
- Launch agent keeps the server running (auto-start on login, auto-restart on crash)
- Cron jobs handle scanning and backups automatically
- CLI commands for manual control when needed
- Backup/restore for disaster recovery

## Configuration

### Environment Variables
Copy `.env.example` to `.env`:
```bash
HERMES_STATE_DB=~/.hermes/state.db   # Path to Hermes state.db
PORT=9876                             # Wiki server port
```

### Adding Custom Project Categories
Edit `scripts/scan_sessions.py` → `PROJECTS` list:
```python
PROJECTS = [
    {
        "name": "Your Project Name",
        "emoji": "🔥",
        "description": "What this project is about",
        "keywords": ["keyword1", "keyword2", "keyword3"],
    },
    # ... add more
]
```
The classifier matches against session titles and first user messages.

### Hermes Cron Jobs (Auto-Configured)
| Job | Schedule | Purpose |
|-----|----------|---------|
| Memory Wiki Auto-Scan | Every 1 hour | Scans new sessions, generates summaries |
| Memory Wiki Daily Backup | Daily at 2:00 AM | Creates backup tarball |
| Daily Priority Check-in | Daily at 9:00 AM | Asks for daily priority (optional) |

View all cron jobs:
```bash
hermes cron list
```

### Port Conflicts
If port 9876 is in use:
```bash
# Change -p 9876 in ~/Library/LaunchAgents/com.memory-wiki.plist
launchctl unload ~/Library/LaunchAgents/com.memory-wiki.plist
launchctl load ~/Library/LaunchAgents/com.memory-wiki.plist
```

## Uninstall

Completely remove Hermes Memory Wiki:

```bash
cd ~/workspace/hermes-memory-wiki
bash scripts/uninstall.sh
```

The uninstaller will:
1. ✅ Stop the wiki server and unload the launch agent
2. ✅ Remove the launch agent plist
3. ✅ Remove Hermes cron jobs (auto-scan, backup, priority check-in)
4. ✅ Remove the `memory-wiki` CLI
5. ✅ Remove the wiki-context skill
6. ✅ Remove the wiki directory (`~/workspace/hermes-memory-wiki`)
7. ✅ Optionally remove backups (`~/memory-wiki-backups/`)

**Note:** Your Hermes conversation data in `~/.hermes/state.db` is never touched.

## Backup & Restore

**Backups** are created daily at 2:00 AM → `~/memory-wiki-backups/` as timestamped tarballs.

Includes: all session data, Hermes state.db, launch agent and skill configs, wiki source code.

**Restore** on the same or new machine:
```bash
memory-wiki restore memory-wiki-backup_20260528_020000.tar.gz
```

Manual backup anytime:
```bash
memory-wiki backup
```

## Troubleshooting

**Wiki server not loading:**
```bash
memory-wiki status
memory-wiki restart
cat ~/workspace/hermes-memory-wiki/.server-error.log
```

**Sessions not appearing in wiki:**
```bash
memory-wiki rescan
```

**Context not injecting in new sessions:**
```bash
# Verify wiki index exists and is recent
ls -la ~/workspace/hermes-memory-wiki/data/wiki-index.json
memory-wiki rescan
# Check skill file
cat ~/.hermes/skills/hermes-memory-wiki/SKILL.md
```

## Requirements

- **macOS** (launch agent support)
- **Hermes Agent** ([install](https://hermes-agent.nousresearch.com))
- **Node.js** v18+ ([install](https://nodejs.org))
- **Python** v3.8+ (stdlib only)
- **Git** (for cloning)

## Contributing

Contributions welcome! Areas of interest:
- Additional project classification keywords
- Windows/Linux support (currently macOS-only)
- Enhanced summary generation strategies
- Alternative frontend themes

## License

[MIT](LICENSE) — use it freely, modify it, share it.
