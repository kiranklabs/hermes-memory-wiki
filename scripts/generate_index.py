#!/usr/bin/env python3
"""
Generate a compact wiki index from the Memory Wiki data.
Outputs wiki-index.json with all projects and their session summaries,
optimized for quick context injection (~2-3KB total).
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
OUTPUT = DATA_DIR / "wiki-index.json"

def generate_index():
    sessions = json.load(open(DATA_DIR / "sessions.json"))
    projects = json.load(open(DATA_DIR / "projects.json"))

    # Build a compact index
    index = {
        "generated": None,
        "total_sessions": len(sessions),
        "total_projects": len(projects),
        "projects": [],
        "quick_lookup": {},  # keyword -> project name mapping
    }

    from datetime import datetime, timezone
    index["generated"] = datetime.now(tz=timezone.utc).isoformat()

    # Quick lookup keywords
    keyword_map = {}
    keyword_map.update({
        "resume": "Documents & Writing", "cv": "Documents & Writing", "cover letter": "Documents & Writing",
        "document": "Documents & Writing", "pdf": "Documents & Writing", "writing": "Documents & Writing",
        "website": "Personal Website", "portfolio": "Personal Website", "blog": "Personal Website",
        "memory wiki": "Memory Wiki", "wiki": "Memory Wiki",
        "youtube": "YouTube & Video", "video": "YouTube & Video", "shorts": "YouTube & Video",
        "career": "Career Research", "job": "Career Research", "company": "Career Research",
        "hermes": "Hermes Configuration", "config": "Hermes Configuration", "model": "Hermes Configuration",
        "telegram": "Telegram Bot", "bot": "Telegram Bot",
        "mcp": "MCP Servers", "zapier": "MCP Servers", "gmail": "MCP Servers",
        "github": "GitHub & Repo Management", "repo": "GitHub & Repo Management",
        "agent": "AI Agents & Multi-Agent", "multi-agent": "AI Agents & Multi-Agent",
        "token": "Token Optimization", "cost": "Token Optimization",
    })

    for project in projects:
        if project["name"] == "Greetings & Casual":
            continue

        project_entry = {
            "name": project["name"],
            "emoji": project.get("emoji", "📁"),
            "description": project["description"],
            "session_count": project["session_count"],
            "last_session": None,
            "sessions": [],
        }

        # Find sessions for this project
        project_sessions = [s for s in sessions if s.get("project") == project["name"]]
        project_sessions.sort(key=lambda x: x.get("started_at") or "", reverse=True)

        for s in project_sessions:
            dialectic = s.get("dialectic") or {}
            session_entry = {
                "id": s["id"],
                "title": s.get("auto_title") or s.get("title") or "(untitled)",
                "summary": s.get("summary", ""),
                "dialectic_context": dialectic.get("context", ""),
                "reasoning": dialectic.get("reasoning", ""),
                "date": s.get("date"),
                "source": s.get("source", ""),
            }
            project_entry["sessions"].append(session_entry)

        if project_sessions:
            project_entry["last_session"] = project_sessions[0].get("date")

        index["projects"].append(project_entry)

    # Add quick lookup
    index["quick_lookup"] = keyword_map

    with open(OUTPUT, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"✅ Wiki index generated: {len(index['projects'])} projects, {size_kb:.1f}KB")


if __name__ == "__main__":
    generate_index()
