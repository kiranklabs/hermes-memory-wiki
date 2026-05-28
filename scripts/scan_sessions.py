#!/usr/bin/env python3
"""
scan_sessions.py - Extracts session data from Hermes state.db
and generates JSON files for the Hermes Memory Wiki.

Version: 2.5
Changelog:
  2.5 - Facts layer (facts.json) with auto-categorization
         Decisions layer (decisions.json) with supersedence trail
         Cron job classification (auto_scan, backup, priority_check)
         Parallel LLM processing (3 workers)
         Incremental scanning + date filter (days_back)
         Narrative session summaries (no bullets)
         Facts & Decisions pages with dynamic rendering
  2.1 - Skip cron sessions, short sessions (< 3 msgs), scanner self-sessions
       - Tightened Memory Wiki project keywords
  2.0 - Multi-pass dialectic reasoning

Outputs:
  data/sessions.json      - all sessions with metadata + LLM summaries
  data/projects.json     - sessions grouped into projects/work-areas
  data/daily_logs.json   - sessions grouped by day
  data/facts.json        - deduplicated facts extracted from sessions
  data/decisions.json    - decisions with supersedence trail
  data/sessions/*.json   - full message content per session

Usage:
  python3 scan_sessions.py    # scan + LLM summaries for all
"""

import sqlite3
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

DB_PATH = os.path.expanduser("~/.hermes/state.db")
OUT_DIR = Path(__file__).parent.parent / "data"
SESSIONS_DIR = OUT_DIR / "sessions"

# ── Cron job classification ─────────────────────────────────────────────
CRON_CATEGORIES = {
    "auto_scan": ["scan", "auto-scan", "session scan", "wiki scan"],
    "backup": ["backup", "daily backup", "wiki backup"],
    "priority_check": ["priority", "check-in", "daily priority"],
}

def classify_cron_job(title, messages_text):
    text = (title + " " + messages_text).lower()
    for category, keywords in CRON_CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return category
    return "other"

# ── Project classification ──────────────────────────────────────────────
PROJECTS = [
    {
        "name": "Memory Wiki",
        "emoji": "⚡",
        "description": "Building and improving the Hermes Memory Wiki ecosystem",
        "keywords": ["memory-wiki", "scan_sessions", "memory wiki site",
                     "memory wiki server", "memory wiki ecosystem"],
    },
    {
        "name": "Personal Website",
        "emoji": "🌐",
        "description": "Building and maintaining a personal website",
        "keywords": ["personal website", "portfolio", "next.js", "tailwind",
                     "vercel", "framer motion", "shadcn", "blog"],
    },
    {
        "name": "Documents & Writing",
        "emoji": "📄",
        "description": "Creating, editing, and managing documents and written content",
        "keywords": ["resume", "cover letter", "cv", "document", "pdf", "writing",
                     "template", "generator", "nano-pdf", "ocr"],
    },
    {
        "name": "Career Research",
        "emoji": "🔍",
        "description": "Company research, job search strategy, and applications",
        "keywords": ["career research", "target companies", "job search",
                     "applying to roles", "interview prep"],
    },
    {
        "name": "YouTube & Video",
        "emoji": "🎬",
        "description": "YouTube video creation, Shorts, and content strategy",
        "keywords": ["youtube", "shorts", "video generation", "comfyui",
                     "photorealistic", "video creation"],
    },
    {
        "name": "GitHub & Repo Management",
        "emoji": "🐙",
        "description": "GitHub repository review, licensing, and CI/CD automation",
        "keywords": ["github", "gh cli", "pull request", "github actions",
                     "license file", "repo review", "open source"],
    },
    {
        "name": "Hermes Configuration",
        "emoji": "⚙️",
        "description": "Setting up and configuring Hermes agent, models, and tools",
        "keywords": ["hermes config", "hermes setup", "gateway", "model", "provider",
                     "openrouter", "personality", "toolsets"],
    },
    {
        "name": "Telegram Bot",
        "emoji": "✈️",
        "description": "Setting up and using the Telegram bot integration",
        "keywords": ["telegram", "telegram bot", "telegram group", "bot token"],
    },
    {
        "name": "MCP Servers",
        "emoji": "🔌",
        "description": "Connecting and configuring MCP servers",
        "keywords": ["mcp server", "mcp", "zapier", "gmail mcp", "native-mcp"],
    },
    {
        "name": "AI Agents & Multi-Agent",
        "emoji": "🤖",
        "description": "Creating multiple agents, autonomous agents, and orchestration",
        "keywords": ["multiple agents", "autonomous agent", "agent orchestration",
                     "subagent", "delegate_task", "kanban orchestrator"],
    },
    {
        "name": "Token Optimization",
        "emoji": "📊",
        "description": "Optimizing token usage, context management, and cost reduction",
        "keywords": ["token usage", "input token", "context", "optimize", "cost",
                     "token count", "context window"],
    },
    {
        "name": "Greetings & Casual",
        "emoji": "👋",
        "description": "Quick greetings, check-ins, and casual conversations",
        "keywords": [],
        "is_default": True,
    },
]

FACT_CATEGORIES = ["environment", "preferences", "tools", "conventions", "constraints"]


# ── Helpers ──────────────────────────────────────────────────────────────

def ts_to_dt(ts):
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (OSError, ValueError, OverflowError):
        return None

def ts_to_date(ts):
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OSError, ValueError, OverflowError):
        return None

def run_hermes_prompt(prompt, max_chars=4000):
    try:
        result = subprocess.run(
            ["hermes", "-z", prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:max_chars]
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return ""

def clean_text(text, max_len=200):
    text = re.sub(r'##.*?\n', '', text)
    text = re.sub(r'\[System note:.*?\]', '', text)
    text = re.sub(r'>.*?\n', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = text.replace('\n', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text

def get_session_messages(conn, session_id):
    cur = conn.execute(
        """SELECT role, content, tool_name, timestamp
           FROM messages WHERE session_id = ? ORDER BY timestamp ASC""",
        (session_id,)
    )
    messages = []
    for row in cur:
        content = row[1] or ""
        if len(content.strip()) < 3 and row[2] is None:
            continue
        messages.append({
            "role": row[0],
            "content": content[:3000],
            "tool_name": row[2],
            "timestamp": ts_to_dt(row[3]),
        })
    return messages

def classify_project(title, user_messages, assistant_messages):
    all_text = (title or "") + " "
    all_text += " ".join(user_messages[:10]) + " "
    all_text += " ".join(assistant_messages[:5])
    all_text = all_text.lower()
    for project in PROJECTS:
        if project.get("is_default"):
            continue
        for kw in project["keywords"]:
            if kw in all_text:
                return project
    if len(user_messages) <= 2 and len(all_text) < 200:
        return next(p for p in PROJECTS if p.get("is_default"))
    return None

def classify_fact_category(fact_text):
    text = fact_text.lower()
    scores = {
        "environment": sum(1 for k in ["macos", "linux", "windows", "ubuntu", "machine", "computer", "device", "hardware"] if k in text),
        "tools": sum(1 for k in ["python", "node", "react", "docker", "tool", "library", "framework", "package", "cli"] if k in text),
        "conventions": sum(1 for k in ["convention", "pattern", "style", "always", "never", "should", "must", "rule", "format"] if k in text),
        "constraints": sum(1 for k in ["limit", "cannot", "can't", "avoid", "bound", "capped", "max", "min"] if k in text),
        "preferences": sum(1 for k in ["prefer", "like", "rather", "choose", "want", "favorite"] if k in text),
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "preferences"


# ── LLM summarization ───────────────────────────────────────────────────

def llm_summarize(messages, title, project_name):
    """Generate a complete session summary + title + facts + decisions via LLM.

    Returns dict with:
      - summary: Narrative paragraph (what happened, outcomes, takeaways)
      - title: LLM-generated descriptive title
      - facts: list of {fact, category}
      - decisions: list of decision strings
    """
    user_msgs = [m for m in messages if m["role"] == "user"]
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    tool_msgs = [m for m in messages if m["role"] == "tool"]

    if not user_msgs:
        return {
            "summary": "No conversation content in this session.",
            "title": title or "(untitled)",
            "facts": [],
            "decisions": [],
        }

    # Build compact excerpt - first 2 user + first 2 assistant messages, truncated
    excerpt_parts = []
    for m in (user_msgs[:2] + assistant_msgs[:2]):
        role = "User" if m["role"] == "user" else "Assistant"
        content = clean_text(m["content"], 250)
        if content:
            excerpt_parts.append(f"{role}: {content}")
    excerpt = "\n".join(excerpt_parts)

    tools_used = list(set(m["tool_name"] for m in tool_msgs if m["tool_name"]))
    tools_str = ", ".join(tools_used[:5]) if tools_used else "none"

    prompt = f"""Analyze this conversation session and provide a structured summary.

Project: {project_name}
Tools used: {tools_str}

Conversation excerpt:
{excerpt}

Provide output in this exact format:

---SUMMARY---
[3-4 sentence narrative: What was the session about? What did the user ask? What was built/done? Key takeaways? Third person, factual.]

---TITLE---
[Short descriptive title, 4-8 words, no punctuation]

---FACTS---
[One fact per line, format: fact text | category]
[Categories: environment, preferences, tools, conventions, constraints]
[Only clear factual statements, 0-5 facts]

---DECISIONS---
- [One decision per line]
- [Only decisions made by the USER. What did the user decide, choose, or want? Do NOT include decisions or actions taken by the assistant.]
- [0-5 decisions]"""

    result = run_hermes_prompt(prompt, max_chars=4000)

    if not result:
        # Fallback: heuristic
        first_q = user_msgs[0]["content"].strip()[:120]
        return {
            "summary": f"The user asked about {first_q}",
            "title": first_q[:60],
            "facts": [],
            "decisions": [],
        }

    # Parse sections
    def extract_section(text, tag):
        start = text.find(tag)
        if start < 0:
            return ""
        start += len(tag)
        end = len(text)
        all_tags = ["---SUMMARY---", "---TITLE---", "---FACTS---", "---DECISIONS---"]
        for next_tag in all_tags:
            if next_tag != tag:
                pos = text.find(next_tag, start)
                if pos >= 0 and pos < end:
                    end = pos
        return text[start:end].strip()

    summary_section = extract_section(result, "---SUMMARY---")
    title_section = extract_section(result, "---TITLE---")
    facts_section = extract_section(result, "---FACTS---")
    decisions_section = extract_section(result, "---DECISIONS---")

    # Parse facts
    facts = []
    if facts_section:
        for line in facts_section.split("\n"):
            line = line.strip()
            # Skip empty lines, bracketed instructions, and delimiter artifacts
            if not line or line.startswith("[") or line.startswith("---") or line.startswith("Only "):
                continue
            # Skip lines that are clearly LLM prompt artifacts
            if any(k in line.lower() for k in ["categories:", "one fact per line", "0-5 facts", "fact text | category"]):
                continue
            fact_text = line
            cat = "preferences"
            if "|" in line:
                parts = line.rsplit("|", 1)
                fact_text = parts[0].strip().strip("[] ")
                cat_raw = parts[1].strip().strip("[] ").lower()
                if cat_raw in FACT_CATEGORIES:
                    cat = cat_raw
                else:
                    cat = classify_fact_category(fact_text)
            else:
                cat = classify_fact_category(fact_text)
            # Skip meta/analytic sentences about the session itself
            if any(k in fact_text.lower() for k in [
                "the user requested", "the user asked", "the assistant", "this session",
                "the conversation", "no actual work", "no files were", "the task was",
                "the excerpt", "the point of summary", "the interaction was",
                "the user sent", "there were no", "the rules specified"
            ]):
                continue
            if fact_text and len(fact_text) > 10 and len(fact_text) < 200:
                facts.append({"fact": fact_text, "category": cat})

    # Parse decisions
    decisions = []
    if decisions_section:
        for line in decisions_section.split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line and len(line) > 5 and not line.startswith("["):
                decisions.append(line)

    return {
        "summary": summary_section or f"Session about {project_name}.",
        "title": title_section.strip() if title_section.strip() else (title or "(untitled)"),
        "facts": facts,
        "decisions": decisions,
    }


# ── Fact/Decision deduplication ──────────────────────────────────────────

def merge_facts(accumulated, new_facts, session_id):
    for item in new_facts:
        fact_text = item["fact"]
        category = item.get("category", "preferences")
        key = re.sub(r'\s+', ' ', fact_text.lower().strip())[:80]
        if key in accumulated:
            if session_id not in accumulated[key].get("sessions", []):
                accumulated[key].setdefault("sessions", []).append(session_id)
            if category != "preferences" and accumulated[key].get("category") == "preferences":
                accumulated[key]["category"] = category
        else:
            accumulated[key] = {
                "fact": fact_text,
                "category": category,
                "sessions": [session_id],
                "first_seen": datetime.now(timezone.utc).isoformat(),
            }
    return accumulated

def merge_decisions(accumulated, new_decisions, session_id):
    for dec_text in new_decisions:
        key = re.sub(r'\s+', ' ', dec_text.lower().strip())[:80]
        if key in accumulated:
            if session_id not in accumulated[key].get("sessions", []):
                accumulated[key].setdefault("sessions", []).append(session_id)
        else:
            accumulated[key] = {
                "decision": dec_text,
                "sessions": [session_id],
                "first_seen": datetime.now(timezone.utc).isoformat(),
            }
    return accumulated


# ── Main scan ────────────────────────────────────────────────────────────

def scan(days_back=7):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Calculate date cutoff
    cutoff = datetime.now(timezone.utc).timestamp() - (days_back * 86400)

    # ── Phase 1: Collect session data (fast, no LLM) ─────────────────────
    pending = []  # User sessions to summarize
    cron_jobs = []  # Cron job sessions (separate from wiki)

    # Initialize output structures (needed for incremental scan fallback)
    sessions_out = []
    project_map = defaultdict(lambda: {"sessions": [], "description": "", "emoji": ""})
    daily_logs = defaultdict(list)

    cur = conn.execute(
        """SELECT id, title, source, started_at, ended_at,
                  message_count, tool_call_count, input_tokens, output_tokens
           FROM sessions WHERE started_at >= ?
           ORDER BY started_at DESC""",
        (cutoff,)
    )

    for row in cur:
        sid = row[0]
        title = row[1] or "(untitled)"
        source = row[2]
        started_at = row[3]
        date_str = ts_to_date(started_at)
        messages = get_session_messages(conn, sid)

        # Handle cron sessions separately
        if source == "cron":
            cron_cat = classify_cron_job(title, " ".join(m["content"] for m in messages if m["role"] == "user"))
            cron_jobs.append({
                "id": sid,
                "title": title,
                "category": cron_cat,
                "started_at": ts_to_dt(started_at),
                "date": date_str,
                "message_count": row[5] or 0,
            })
            continue

        if len(messages) < 3:
            continue
        user_msg_check = [m["content"] for m in messages if m["role"] == "user"]
        if any("---PASS" in msg or "3 reasoning passes" in msg for msg in user_msg_check):
            continue

        user_msg_texts = [m["content"] for m in messages if m["role"] == "user"]
        asst_msg_texts = [m["content"] for m in messages if m["role"] == "assistant"]
        project = classify_project(title, user_msg_texts, asst_msg_texts)
        project_name = project["name"] if project else "Other"

        # Skip sessions that already have an LLM summary (incremental scan)
        # Check using the existing sessions.json index to avoid reading all files
        session_file = SESSIONS_DIR / f"{sid}.json"
        if session_file.exists():
            try:
                existing = json.loads(session_file.read_text())
                if existing.get("summary") and len(existing["summary"]) > 20 and existing.get("auto_title"):
                    # Already summarized - reuse
                    sessions_out.append({
                        "id": sid, "title": existing.get("title", title),
                        "auto_title": existing.get("auto_title"), "summary": existing.get("summary"),
                        "project": existing.get("project", project_name), "source": source,
                        "started_at": existing.get("started_at") or ts_to_dt(started_at),
                        "ended_at": existing.get("ended_at") or ts_to_dt(row[4]),
                        "date": existing.get("date") or date_str,
                        "message_count": existing.get("message_count", row[5] or 0),
                        "tool_call_count": existing.get("tool_call_count", row[6] or 0),
                        "input_tokens": existing.get("input_tokens", row[7] or 0),
                        "output_tokens": existing.get("output_tokens", row[8] or 0),
                    })
                    project_map[project_name]["sessions"].append(sid)
                    if project:
                        project_map[project_name]["description"] = project["description"]
                        project_map[project_name]["emoji"] = project["emoji"]
                    if date_str:
                        daily_logs[date_str].append({
                            "id": sid, "title": title, "auto_title": existing.get("auto_title"),
                            "summary": existing.get("summary"), "project": project_name,
                            "source": source, "message_count": row[5] or 0,
                        })
                    continue
            except:
                pass

        pending.append({
            "sid": sid,
            "title": title,
            "source": source,
            "started_at": started_at,
            "date_str": date_str,
            "row": row,
            "messages": messages,
            "project_name": project_name,
            "project": project,
        })

    conn.close()

    # ── Phase 2: LLM summarization in parallel ───────────────────────────
    accumulated_facts = {}
    accumulated_decisions = {}

    def process_session(data):
        """Process a single session: run LLM, return session data + facts + decisions."""
        result = llm_summarize(data["messages"], data["title"], data["project_name"])
        return {
            "data": data,
            "summary": result["summary"],
            "auto_title": result["title"],
            "facts": result["facts"],
            "decisions": result["decisions"],
        }

    # Use ThreadPoolExecutor for parallel LLM calls
    # Limit to 3 concurrent to avoid overwhelming the LLM
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_session, p): p for p in pending}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                p = futures[future]
                print(f"  Warning: failed to summarize {p['sid']}: {e}")
                results.append({
                    "data": p,
                    "summary": f"Error summarizing session.",
                    "auto_title": p["title"],
                    "facts": [],
                    "decisions": [],
                })

    # ── Phase 3: Write output files ──────────────────────────────────────
    project_map = defaultdict(lambda: {"sessions": [], "description": "", "emoji": ""})
    daily_logs = defaultdict(list)

    for r in results:
        d = r["data"]
        sid = d["sid"]
        summary = r["summary"]
        auto_title = r["auto_title"]
        facts = r["facts"]
        decisions_extracted = r["decisions"]

        if facts:
            merge_facts(accumulated_facts, facts, sid)
        if decisions_extracted:
            merge_decisions(accumulated_decisions, decisions_extracted, sid)

        session_data = {
            "id": sid,
            "title": d["title"],
            "auto_title": auto_title,
            "summary": summary,
            "project": d["project_name"],
            "source": d["source"],
            "started_at": ts_to_dt(d["started_at"]),
            "ended_at": ts_to_dt(d["row"][4]),
            "date": d["date_str"],
            "message_count": d["row"][5] or 0,
            "tool_call_count": d["row"][6] or 0,
            "input_tokens": d["row"][7] or 0,
            "output_tokens": d["row"][8] or 0,
            "messages": d["messages"],
        }

        with open(SESSIONS_DIR / f"{sid}.json", "w") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        sessions_out.append({k: v for k, v in session_data.items() if k != "messages"})

        project_map[d["project_name"]]["sessions"].append(sid)
        if d["project"]:
            project_map[d["project_name"]]["description"] = d["project"]["description"]
            project_map[d["project_name"]]["emoji"] = d["project"]["emoji"]

        if d["date_str"]:
            daily_logs[d["date_str"]].append({
                "id": sid,
                "title": d["title"],
                "auto_title": auto_title,
                "summary": summary,
                "project": d["project_name"],
                "source": d["source"],
                "message_count": d["row"][5] or 0,
            })

    # Write sessions index
    with open(OUT_DIR / "sessions.json", "w") as f:
        json.dump(sessions_out, f, indent=2, ensure_ascii=False)

    # Write projects
    projects_out = [
        {
            "name": k,
            "emoji": v.get("emoji", "📁"),
            "description": v.get("description", ""),
            "session_count": len(v["sessions"]),
            "sessions": v["sessions"],
        }
        for k, v in project_map.items()
    ]
    projects_out.sort(key=lambda x: (x["name"] == "Greetings & Casual", -x["session_count"]))
    with open(OUT_DIR / "projects.json", "w") as f:
        json.dump(projects_out, f, indent=2, ensure_ascii=False)

    # Write daily logs
    daily_out = [
        {
            "date": k,
            "session_count": len(v),
            "sessions": v,
            "projects": sorted(set(s["project"] for s in v)),
        }
        for k, v in daily_logs.items()
    ]
    daily_out.sort(key=lambda x: x["date"], reverse=True)
    with open(OUT_DIR / "daily_logs.json", "w") as f:
        json.dump(daily_out, f, indent=2, ensure_ascii=False)

    # Write facts
    facts_list = []
    for key, v in sorted(accumulated_facts.items()):
        facts_list.append({
            "id": f"fact_{len(facts_list) + 1:03d}",
            "fact": v.get("fact", key),
            "category": v.get("category", "preferences"),
            "sessions": v.get("sessions", []),
            "first_seen": v.get("first_seen"),
            "status": "active",
        })
    with open(OUT_DIR / "facts.json", "w") as f:
        json.dump({
            "version": "1.0",
            "generated": datetime.now(timezone.utc).isoformat(),
            "facts": facts_list,
        }, f, indent=2, ensure_ascii=False)

    # Write decisions
    decisions_list = []
    for key, v in sorted(accumulated_decisions.items()):
        decisions_list.append({
            "id": f"dec_{len(decisions_list) + 1:03d}",
            "decision": v.get("decision", key),
            "sessions": v.get("sessions", []),
            "first_seen": v.get("first_seen"),
            "status": "active",
        })
    with open(OUT_DIR / "decisions.json", "w") as f:
        json.dump({
            "version": "1.0",
            "generated": datetime.now(timezone.utc).isoformat(),
            "decisions": decisions_list,
        }, f, indent=2, ensure_ascii=False)

    # Write cron jobs
    cron_jobs.sort(key=lambda x: x["started_at"] or "", reverse=True)
    with open(OUT_DIR / "cron-jobs.json", "w") as f:
        json.dump({
            "version": "1.0",
            "generated": datetime.now(timezone.utc).isoformat(),
            "cron_jobs": cron_jobs,
        }, f, indent=2, ensure_ascii=False)

    print(f"Scanned {len(sessions_out)} sessions, {len(projects_out)} projects, {len(daily_out)} days")
    print(f"Extracted {len(facts_list)} unique facts, {len(decisions_list)} unique decisions")
    print(f"Cron jobs: {len(cron_jobs)}")

    # Rebuild all index files from session data to ensure consistency
    print("\nRebuilding index files...")
    # Look for rebuild_data.py in the scanner's script directory
    rebuild_script = Path(__file__).parent / "rebuild_data.py"
    if rebuild_script.exists():
        result = subprocess.run(
            [sys.executable, str(rebuild_script)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("Index rebuild complete.")
        else:
            print(f"Index rebuild failed: {result.stderr}")


if __name__ == "__main__":
    scan(days_back=7)
