#!/usr/bin/env python3
"""
scan_sessions.py — Extracts session data from Hermes state.db
and generates JSON files for the Memory Wiki.

Environment variables:
  HERMES_STATE_DB  Path to Hermes state.db (default: ~/.hermes/state.db)

Outputs:
  data/sessions.json      — all sessions with metadata
  data/projects.json     — sessions grouped into projects/work-areas
  data/daily_logs.json    — sessions grouped by day
  data/sessions/*.json    — full message content per session

Usage:
  python3 scan_sessions.py              # scan only
  python3 scan_sessions.py --summarize  # scan + generate narrative summaries
"""

import sqlite3
import json
import os
import re
import sys
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

DB_PATH = Path(os.environ.get("HERMES_STATE_DB", os.path.expanduser("~/.hermes/state.db")))
OUT_DIR = Path(__file__).parent.parent / "data"  # Wiki data output directory
SESSIONS_DIR = OUT_DIR / "sessions"

# ── Project classification ──────────────────────────────────────────────
# Each project has a name, description, and keyword triggers that indicate
# a session belongs to it. Order matters — first match wins.
PROJECTS = [
    {
        "name": "Memory Wiki",
        "emoji": "⚡",
        "description": "Building the Memory Wiki site to browse conversation history",
        "keywords": ["memory wiki", "session scanner", "memory-wiki", "session data",
                     "browsable record", "daily logs", "subjects we've talked"],
    },
    {
        "name": "Personal Website",
        "emoji": "🌐",
        "description": "Building and maintaining a personal website or portfolio",
        "keywords": ["personal website", "portfolio", "next.js", "tailwind",
                     "vercel", "framer motion", "shadcn", "blog"],
    },
    {
        "name": "Resume System",
        "emoji": "📄",
        "description": "Building the resume generator and cover letter system",
        "keywords": ["resume", "cover letter", "cv template", "resume system",
                     "resume template", "cv generator"],
    },
    {
        "name": "Career Research",
        "emoji": "🔍",
        "description": "Company research, job search strategy, and application automation",
        "keywords": ["career research", "target companies", "job search", "applying to roles",
                     "career research assistant", "qualified prioritized list"],
    },
    {
        "name": "YouTube & Video",
        "emoji": "🎬",
        "description": "YouTube video creation, Shorts, and content strategy",
        "keywords": ["youtube", "shorts", "video generation", "comfyui", "ayurveda",
                     "fasting videos", "photorealistic"],
    },
    {
        "name": "GitHub & Repo Management",
        "emoji": "🐙",
        "description": "GitHub repository review, licensing, and CI/CD automation",
        "keywords": ["github", "gh cli", "pull request", "github actions", "license file",
                     "repo review", "open source"],
    },
    {
        "name": "Hermes Configuration",
        "emoji": "⚙️",
        "description": "Setting up and configuring Hermes agent, models, and tools",
        "keywords": ["hermes config", "hermes setup", "gateway", "model", "provider",
                     "openrouter", "personality", "toolsets", "hermes kickoff"],
    },
    {
        "name": "Telegram Bot",
        "emoji": "✈️",
        "description": "Setting up and using the Telegram bot integration",
        "keywords": ["telegram", "telegram bot", "telegram group", "add you to a group",
                     "bot token"],
    },
    {
        "name": "MCP Servers",
        "emoji": "🔌",
        "description": "Connecting and configuring MCP servers (Zapier, Gmail, etc.)",
        "keywords": ["mcp server", "mcp", "zapier", "gmail mcp", "config.yaml mcp",
                     "native-mcp"],
    },
    {
        "name": "AI Agents & Multi-Agent",
        "emoji": "🤖",
        "description": "Creating multiple agents, autonomous agents, and agent orchestration",
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
        "keywords": [],  # fallback — short sessions with no other match
        "is_default": True,
    },
]


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


def classify_project(title, user_messages, assistant_messages):
    """Classify a session into a project based on content."""
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

    # Default: short sessions with no clear topic → Greetings
    if len(user_messages) <= 2 and len(all_text) < 200:
        return next(p for p in PROJECTS if p.get("is_default"))

    return None


def generate_narrative_summary(messages, title, project_name):
    """
    Generate a 4-10 line narrative paragraph summarizing the session.
    Reads the actual conversation to understand what was asked and achieved.
    """
    user_msgs = [m for m in messages if m["role"] == "user"]
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    tool_msgs = [m for m in messages if m["role"] == "tool"]

    if not user_msgs:
        return "No conversation content in this session."

    def clean_text(text, max_len=200):
        """Clean up message text for use in a summary paragraph."""
        # Remove markdown headers, system notes, etc.
        text = re.sub(r'##.*?\n', '', text)
        text = re.sub(r'\[System note:.*?\]', '', text)
        text = re.sub(r'>.*?\n', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = text.replace('\n', ' ').strip()
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        if len(text) > max_len:
            text = text[:max_len] + "…"
        return text

    def first_sentence(text):
        """Extract the first meaningful sentence from text."""
        text = clean_text(text, 300)
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences:
            s = s.strip()
            if len(s) > 15:
                return s
        return text[:120]

    lines = []

    # ── What the user asked ──
    first_user = clean_text(user_msgs[0]["content"], 250)
    for prefix in [
        "i want to ", "i'd like to ", "can you ", "please ", "hey ", "hi ",
        "hello ", "ok ", "yes ", "i need to ", "help me ", "let's ", "i am ",
    ]:
        if first_user.lower().startswith(prefix):
            first_user = first_user[len(prefix):]
            break
    first_user = first_user.strip()
    if first_user:
        first_user = first_user[0].upper() + first_user[1:]
        if not first_user[-1] in ".!?":
            first_user += "."
        lines.append(f"The user asked about {first_user[0].lower()}{first_user[1:]}")

    # ── What I did (from first substantive assistant response) ──
    for msg in assistant_msgs[:5]:
        content = msg["content"].strip()
        # Skip very short or meta responses
        if len(content) < 30:
            continue
        # Skip responses that are just questions back
        if content.strip().endswith("?") and len(content) < 100:
            continue

        # Extract the key action from the response
        action = first_sentence(content)
        if action and len(action) > 20:
            # Clean up the action text
            action = action.strip()
            if not action[-1] in ".!?":
                action += "."
            lines.append(f"I {action[0].lower()}{action[1:]}")
            break

    # ── Follow-up from the user ──
    if len(user_msgs) > 1:
        follow_up = clean_text(user_msgs[1]["content"], 150)
        for prefix in ["i want to ", "i'd like to ", "can you ", "please ",
                        "also ", "ok ", "yes ", "and ", "but ", "so "]:
            if follow_up.lower().startswith(prefix):
                follow_up = follow_up[len(prefix):]
                break
        follow_up = follow_up.strip()
        if follow_up and len(follow_up) > 10:
            follow_up = follow_up[0].upper() + follow_up[1:]
            if not follow_up[-1] in ".!?":
                follow_up += "."
            lines.append(f"The user also {follow_up[0].lower()}{follow_up[1:]}")

    # ── Tools used ──
    tools_used = list(set(m["tool_name"] for m in tool_msgs if m["tool_name"]))
    if tools_used:
        # Clean up tool names
        clean_tools = []
        for t in tools_used[:6]:
            # Remove common prefixes
            t = t.replace("mcp_", "").replace("_", " ").strip()
            if t:
                clean_tools.append(t)
        if clean_tools:
            if len(clean_tools) <= 3:
                tool_str = ", ".join(clean_tools)
            else:
                tool_str = ", ".join(clean_tools[:3]) + f" and {len(clean_tools) - 3} more"
            lines.append(f"I used tools including {tool_str}.")

    # ── Outcome / scope ──
    total_user = len(user_msgs)
    total_asst = len(assistant_msgs)
    if total_user > 10:
        lines.append(f"This was an extensive session with {total_user} exchanges covering multiple aspects and iterations.")
    elif total_user > 5:
        lines.append(f"The session involved {total_user} exchanges with follow-up questions and refinements.")
    elif total_user > 2:
        lines.append(f"The session had {total_user} exchanges with some back-and-forth discussion.")

    # Ensure we have at least 3 lines
    if len(lines) < 3 and assistant_msgs:
        # Add a line from the last assistant message
        last = assistant_msgs[-1]["content"].strip()
        if last:
            last_clean = clean_text(last, 150)
            if len(last_clean) > 20:
                lines.append(f"In response, I {last_clean[0].lower()}{last_clean[1:]}")

    return " ".join(lines)


def get_session_messages(conn, session_id):
    cur = conn.execute(
        """SELECT role, content, tool_name, timestamp 
           FROM messages 
           WHERE session_id = ? 
           ORDER BY timestamp ASC""",
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


def generate_auto_title(messages, existing_title, project_name):
    """Generate a descriptive title from the first user message."""
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if not user_msgs:
        return existing_title or "(untitled)"

    first_msg = user_msgs[0].strip()

    # Remove common prefixes
    clean = first_msg
    for prefix in [
        "i want to ", "i'd like to ", "can you ", "please ", "hey ", "hi ",
        "hello ", "ok ", "yes ", "i need to ", "help me ", "let's ",
    ]:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):]
            break

    # Take first sentence or first 80 chars
    for delim in [".", "!", "?"]:
        idx = clean.find(delim)
        if 10 < idx < 80:
            clean = clean[:idx]
            break
    clean = clean[:80].strip()

    if clean and len(clean) > 5:
        return clean[0].upper() + clean[1:]
    return existing_title or "(untitled)"


def scan(summarize=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    sessions = []
    project_map = defaultdict(lambda: {"sessions": [], "description": "", "emoji": ""})
    daily_logs = defaultdict(list)

    cur = conn.execute(
        """SELECT id, title, source, started_at, ended_at, message_count, 
                  tool_call_count, input_tokens, output_tokens
           FROM sessions 
           ORDER BY started_at DESC"""
    )

    for row in cur:
        sid = row[0]
        title = row[1] or "(untitled)"
        source = row[2]
        started_at = row[3]
        date_str = ts_to_date(started_at)

        messages = get_session_messages(conn, sid)

        # Classify into project
        user_msg_texts = [m["content"] for m in messages if m["role"] == "user"]
        asst_msg_texts = [m["content"] for m in messages if m["role"] == "assistant"]
        project = classify_project(title, user_msg_texts, asst_msg_texts)
        project_name = project["name"] if project else "Other"

        # Generate auto-title
        auto_title = generate_auto_title(messages, title, project_name)

        # Generate narrative summary
        summary = None
        if summarize:
            summary = generate_narrative_summary(messages, title, project_name)

        session_data = {
            "id": sid,
            "title": title,
            "auto_title": auto_title,
            "summary": summary,
            "project": project_name,
            "source": source,
            "started_at": ts_to_dt(started_at),
            "ended_at": ts_to_dt(row[4]),
            "date": date_str,
            "message_count": row[5] or 0,
            "tool_call_count": row[6] or 0,
            "input_tokens": row[7] or 0,
            "output_tokens": row[8] or 0,
            "messages": messages,
        }

        with open(SESSIONS_DIR / f"{sid}.json", "w") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        sessions.append({k: v for k, v in session_data.items() if k != "messages"})

        # Build project map
        project_map[project_name]["sessions"].append(sid)
        if project:
            project_map[project_name]["description"] = project["description"]
            project_map[project_name]["emoji"] = project["emoji"]

        # Build daily logs
        if date_str:
            daily_logs[date_str].append({
                "id": sid,
                "title": title,
                "auto_title": auto_title,
                "summary": summary,
                "project": project_name,
                "source": source,
                "message_count": row[5] or 0,
            })

    conn.close()

    # Write sessions index
    with open(OUT_DIR / "sessions.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

    # Write projects
    projects = [
        {
            "name": k,
            "emoji": v.get("emoji", "📁"),
            "description": v.get("description", ""),
            "session_count": len(v["sessions"]),
            "sessions": v["sessions"],
        }
        for k, v in project_map.items()
    ]
    # Sort: projects with more sessions first, but put "Greetings" last
    projects.sort(key=lambda x: (x["name"] == "Greetings & Casual", -x["session_count"]))
    with open(OUT_DIR / "projects.json", "w") as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)

    # Write daily logs
    daily = [
        {
            "date": k,
            "session_count": len(v),
            "sessions": v,
            "projects": list(set(s["project"] for s in v)),
        }
        for k, v in daily_logs.items()
    ]
    daily.sort(key=lambda x: x["date"], reverse=True)
    with open(OUT_DIR / "daily_logs.json", "w") as f:
        json.dump(daily, f, indent=2, ensure_ascii=False)

    print(f"✅ Scanned {len(sessions)} sessions, {len(projects)} projects, {len(daily)} days")
    if summarize:
        print("   Narrative summaries and auto-titles generated")
    print(f"   Output: {OUT_DIR}")

    # Generate compact wiki index
    try:
        from generate_index import generate_index
        generate_index()
    except Exception as e:
        print(f"   ⚠️  Wiki index generation failed: {e}")


if __name__ == "__main__":
    do_summarize = "--summarize" in sys.argv
    scan(summarize=do_summarize)
