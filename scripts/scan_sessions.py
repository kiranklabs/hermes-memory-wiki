#!/usr/bin/env python3
"""
scan_sessions.py — Extracts session data from Hermes state.db
and generates JSON files for the Memory Wiki.

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
import subprocess
import concurrent.futures
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

DB_PATH = os.path.expanduser("~/.hermes/state.db")
OUT_DIR = Path(__file__).parent.parent / "data"
SESSIONS_DIR = OUT_DIR / "sessions"

# ── Project classification ──────────────────────────────────────────────
# Each project has a name, description, and keyword triggers that indicate
# a session belongs to it. Order matters — first match wins.
PROJECTS = [
    {
        "name": "Memory Wiki",
        "emoji": "⚡",
        "description": "Building and improving the Memory Wiki ecosystem",
        "keywords": ["memory-wiki", "scan_sessions", "memory wiki site",
                     "memory wiki server", "memory wiki ecosystem"],
    },
    {
        "name": "Personal Website",
        "emoji": "🌐",
        "description": "Building and maintaining a personal website or portfolio",
        "keywords": ["personal website", "portfolio", "next.js", "tailwind",
                     "vercel", "framer motion", "shadcn", "blog"],
    },
    {
        "name": "Documents & Writing",
        "emoji": "📄",
        "description": "Creating, editing, and managing documents, PDFs, and written content",
        "keywords": ["resume", "cover letter", "cv", "document", "pdf", "writing",
                     "template", "generator", "nano-pdf", "ocr"],
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
        "keywords": ["youtube", "shorts", "video generation", "comfyui",
                     "photorealistic", "video creation"],
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


def run_hermes_prompt(prompt, max_chars=3000):
    """
    Run a prompt through hermes CLI and return the response.
    Falls back to empty string if hermes is not available or fails.
    Uses a single call with multi-pass instructions to avoid N× subprocess overhead.
    """
    try:
        result = subprocess.run(
            ["hermes", "-z", prompt],
            capture_output=True, text=True, timeout=90
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:max_chars]
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return ""


def generate_dialectic_summary(messages, title, project_name, previous_summaries=None):
    """
    Generate a multi-pass dialectic summary using a single LLM call.

    The prompt asks the LLM to run 3 reasoning passes internally:
    Pass 1 — Extract: What was asked, done, decided, accomplished.
    Pass 2 — Reason: What patterns and preferences emerge? What context
             matters most for future sessions on this topic?
    Pass 3 — Synthesize: A concise paragraph optimized for context injection.

    Returns a dict with 'narrative' (fallback heuristic), 'reasoning' (pass 2),
    'context' (pass 3), and 'pass1' (pass 1).
    """
    user_msgs = [m for m in messages if m["role"] == "user"]
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    tool_msgs = [m for m in messages if m["role"] == "tool"]

    if not user_msgs:
        return {
            "narrative": "No conversation content in this session.",
            "reasoning": "",
            "context": "",
            "pass1": "",
            "pass2": "",
        }

    def clean_text(text, max_len=200):
        text = re.sub(r'##.*?\n', '', text)
        text = re.sub(r'\[System note:.*?\]', '', text)
        text = re.sub(r'>.*?\n', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = text.replace('\n', ' ').strip()
        text = re.sub(r'\s+', ' ', text)
        if len(text) > max_len:
            text = text[:max_len] + "…"
        return text

    # Build a compact conversation excerpt — first 3 user + first 2 assistant messages
    excerpt_parts = []
    for m in (user_msgs[:3] + assistant_msgs[:2]):
        role = "User" if m["role"] == "user" else "Assistant"
        content = clean_text(m["content"], 500)
        if content:
            excerpt_parts.append(f"{role}: {content}")
    excerpt = "\n".join(excerpt_parts)

    tools_used = list(set(m["tool_name"] for m in tool_msgs if m["tool_name"]))
    tools_str = ", ".join(tools_used[:5]) if tools_used else "none"

    # Build previous session context for cross-referencing
    prev_context = ""
    if previous_summaries:
        prev_snippets = []
        for s in previous_summaries[:5]:
            ctx = s.get("context") or s.get("pass1") or s.get("summary", "") or ""
            if ctx:
                # Take first sentence only to keep compact
                first_sent = re.split(r'(?<=[.!?])\s+', ctx)[0]
                prev_snippets.append(first_sent[:200])
        if prev_snippets:
            prev_context = "\n".join(prev_snippets)

    # Single prompt that asks for all 3 passes in structured output
    dialectic_prompt = f"""Analyze this conversation session through 3 reasoning passes. Output in this exact format:

---PASS1---
[3-5 sentences: What was asked, done, decided, and accomplished. Third person, factual.]

---PASS2---
[2-3 sentences: What patterns, preferences, or setup choices should be remembered for future sessions on this topic? Focus on actionable context.]

---PASS3---
[One paragraph, 4-6 sentences: A rich context summary for an AI assistant. Cover what was accomplished, key decisions/preferences, where things left off, and important technical details (paths, tools, configs). Third person, factual, optimized for context injection.]

Session title: {title}
Project: {project_name}
Tools used: {tools_str}
{"Previous session context from same project:" if prev_context else ""}
{prev_context}

Conversation excerpt:
{excerpt}

Now run all 3 passes. Do not include any other text."""

    result = run_hermes_prompt(dialectic_prompt, max_chars=4000)

    # Parse the structured output
    pass1 = pass2 = pass3 = ""
    if result:
        # Extract each pass section
        for tag, target in [("---PASS1---", "pass1"), ("---PASS2---", "pass2"), ("---PASS3---", "pass3")]:
            start = result.find(tag)
            if start >= 0:
                start += len(tag)
                # Find next tag or end of string
                end = len(result)
                for next_tag in ["---PASS1---", "---PASS2---", "---PASS3---"]:
                    if next_tag != tag:
                        next_pos = result.find(next_tag, start)
                        if next_pos >= 0 and next_pos < end:
                            end = next_pos
                text = result[start:end].strip()
                if target == "pass1":
                    pass1 = text
                elif target == "pass2":
                    pass2 = text
                elif target == "pass3":
                    pass3 = text

    # Fallback narrative (heuristic, no LLM needed)
    narrative_lines = []
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
        narrative_lines.append(f"The user asked about {first_user[0].lower()}{first_user[1:]}")
    narrative = " ".join(narrative_lines) if narrative_lines else f"Session about {title or project_name}."

    return {
        "narrative": narrative,
        "reasoning": pass2,
        "context": pass3 or pass1,
        "pass1": pass1,
        "pass2": pass2,
    }


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
    session_summaries = {}  # sid -> summary dict, for dialectic cross-referencing

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

        # Skip cron sessions — they're automated noise
        if source == "cron":
            continue

        # Skip sessions with too few messages (less than 3 = not meaningful)
        if len(messages) < 3:
            continue

        # Skip sessions that are just the scanner running (dialectic pass outputs as user messages)
        user_msg_texts_check = [m["content"] for m in messages if m["role"] == "user"]
        if any("---PASS" in msg or "3 reasoning passes" in msg for msg in user_msg_texts_check):
            continue

        # Classify into project
        user_msg_texts = [m["content"] for m in messages if m["role"] == "user"]
        asst_msg_texts = [m["content"] for m in messages if m["role"] == "assistant"]
        project = classify_project(title, user_msg_texts, asst_msg_texts)
        project_name = project["name"] if project else "Other"

        # Generate auto-title
        auto_title = generate_auto_title(messages, title, project_name)

        # Generate dialectic summary (multi-pass LLM reasoning)
        summary = None
        dialectic = None
        if summarize:
            # Collect previous session summaries from the same project
            prev_summaries = [
                session_summaries[psid]
                for psid in project_map[project_name]["sessions"]
                if psid in session_summaries
            ]
            dialectic = generate_dialectic_summary(messages, title, project_name, prev_summaries)
            summary = dialectic.get("context") or dialectic.get("pass1") or dialectic.get("narrative")

        session_data = {
            "id": sid,
            "title": title,
            "auto_title": auto_title,
            "summary": summary,
            "dialectic": dialectic,
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

        # Store dialectic summary for cross-referencing in later sessions
        if dialectic:
            session_summaries[sid] = dialectic

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
