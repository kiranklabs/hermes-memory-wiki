#!/usr/bin/env python3
"""
rebuild_all.py — Rebuild ALL wiki data files from scratch from session files.
Run this after every scan to ensure data consistency.

Usage: python3 scripts/rebuild_all.py
"""

import json
import os
import re
import glob
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
SESSIONS_DIR = Path(os.path.expanduser("~/.hermes/state.db")).parent.parent / "workspace/memory-wiki/data/sessions"

# ── Step 1: Read all session files ──────────────────────────────────────

def load_sessions():
    """Load all session files into memory."""
    sessions = []
    for sf in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            d = json.load(open(sf))
            if d.get("summary") and len(d.get("summary", "")) > 10:
                # Strip messages to keep index light
                sessions.append({k: v for k, v in d.items() if k != "messages"})
        except:
            pass
    return sessions

# ── Step 2: Build projects ──────────────────────────────────────────────

PROJECTS_EMOJI = {
    "Memory Wiki": "⚡",
    "Personal Website": "🌐",
    "Documents & Writing": "📄",
    "Career Research": "🔍",
    "YouTube & Video": "🎬",
    "GitHub & Repo Management": "🐙",
    "Hermes Configuration": "⚙️",
    "Telegram Bot": "✈️",
    "MCP Servers": "🔌",
    "AI Agents & Multi-Agent": "🤖",
    "Token Optimization": "📊",
}

def build_projects(sessions):
    project_map = defaultdict(lambda: {"sessions": [], "emoji": "📁", "description": ""})
    for s in sessions:
        pname = s.get("project", "Other")
        project_map[pname]["sessions"].append(s["id"])
        project_map[pname]["emoji"] = PROJECTS_EMOJI.get(pname, "📁")
    
    return sorted([
        {"name": k, "emoji": v["emoji"], "description": v["description"],
         "session_count": len(v["sessions"]), "sessions": v["sessions"]}
        for k, v in project_map.items()
        if k != "Greetings & Casual" and len(v["sessions"]) > 0
    ], key=lambda x: -x["session_count"])

# ── Step 3: Build daily logs ────────────────────────────────────────────

def build_daily_logs(sessions):
    daily_map = defaultdict(list)
    for s in sessions:
        if s.get("date"):
            daily_map[s["date"]].append({
                "id": s["id"],
                "title": s.get("title", ""),
                "auto_title": s.get("auto_title", ""),
                "summary": s.get("summary", ""),
                "project": s.get("project", "Other"),
                "source": s.get("source", ""),
                "message_count": s.get("message_count", 0),
            })
    return sorted([
        {"date": k, "session_count": len(v), "sessions": v,
         "projects": sorted(set(s["project"] for s in v))}
        for k, v in daily_map.items()
    ], key=lambda x: x["date"], reverse=True)

# ── Step 4: Build facts ─────────────────────────────────────────────────

META_PATTERNS = [
    r"^no (code|files?|work|output|synthesis|final|meaningful|substantive|actual|video|implementation|conversation)",
    r"^the (session|conversation|task|excerpt|interaction|request) (was|is|ended|began|cut short)",
    r"^(this|the) (session|conversation|excerpt|interaction)",
    r"^key (takeaway|takeaways) (include|includes)",
    r"^(the user|user|the assistant|owl) (requested|asked|initiated|sent|began|started|noted|provided)",
    r"^on \w+ \d+,", r"^---", r"^\[", r"^>",
    r"^all existing functionality",
    r"^no (outcomes?|deliverables?|results?)",
    r"^there were no",
    r"^the (rules?|workflow|process|methodology)",
    r"^owl (surveyed|checked|began|started|attempted)",
    r"^the assistant (began|started|attempted|provided|responded)",
    r"^for the (computer|setup|question)",
    r"^he provided", r"^they (requested|also|wanted)",
    r"^no (tools?|files?|code) (were|was)", r"^however", r"^additionally",
    r"^the user requested", r"^the user asked", r"^the user wanted",
]

def is_meta(text):
    for p in META_PATTERNS:
        if re.match(p, text, re.IGNORECASE):
            return True
    return False

FACT_KEYWORDS = {
    "environment": ["mac", "computer", "machine", "device", "os", "port", "server", "deployed",
                    "localhost", "running on", "hosted", "macos", "ubuntu", "windows"],
    "tools": ["next.js", "react", "tailwind", "python", "docker", "vercel", "github", "typescript",
              "javascript", "node", "mcp", "cli", "api", "database", "framework", "library", "package", "tool"],
    "preferences": ["prefers", "always", "never", "usually", "likes", "style", "theme", "dark",
                    "light", "concise", "brief", "technical", "helpful"],
    "conventions": ["convention", "pattern", "standard", "workflow", "process", "branch", "pr", "review"],
    "constraints": ["cannot", "can't", "must", "limit", "avoid", "constraint", "restrict"],
}

def classify_fact(text):
    tl = text.lower()
    for cat, keywords in FACT_KEYWORDS.items():
        if any(k in tl for k in keywords):
            return cat
    return "preferences"

def is_factual(text):
    tl = text.lower()
    for keywords in FACT_KEYWORDS.values():
        if any(k in tl for k in keywords):
            return True
    return False

def build_facts(sessions):
    all_facts = {}
    for s in sessions:
        summary = s.get("summary", "") or ""
        for sent in re.split(r'(?<=[.!?])\s+', summary):
            sent = sent.strip().strip('"').strip()
            if len(sent) < 15 or len(sent) > 200:
                continue
            if is_meta(sent):
                continue
            if not is_factual(sent):
                continue
            cat = classify_fact(sent)
            key = re.sub(r'\s+', ' ', sent.lower())[:60]
            if key not in all_facts:
                all_facts[key] = {"fact": sent, "category": cat, "sessions": [s["id"]]}
    return [{"id": f"fact_{i+1:03d}", "fact": v["fact"], "category": v["category"],
             "source_session": v["sessions"][0] if v["sessions"] else None,
             "created": datetime.now(timezone.utc).isoformat()[:10], "status": "active"}
            for i, v in enumerate(sorted(all_facts.values(), key=lambda x: (x["category"], x["fact"])))]

# ── Step 5: Build decisions ─────────────────────────────────────────────

def build_decisions(sessions):
    all_decisions = {}
    for s in sessions:
        summary = s.get("summary", "") or ""
        for match in re.finditer(
            r"(?:the user|user)\s+(?:decided|chose|specified|requested|wants?|wanted)\s+(?:to\s+)?([^.]+)",
            summary, re.IGNORECASE
        ):
            text = match.group(0).strip()
            if len(text) > 15:
                key = re.sub(r'\s+', ' ', text.lower())[:60]
                if key not in all_decisions:
                    all_decisions[key] = {"decision": text, "sessions": [s["id"]]}
    return [{"id": f"dec_{i+1:03d}", "decision": v["decision"], "category": "",
             "source_session": v["sessions"][0] if v["sessions"] else None,
             "created": datetime.now(timezone.utc).isoformat()[:10], "status": "active",
             "superseded_by": None}
            for i, v in enumerate(sorted(all_decisions.values(), key=lambda x: x["decision"]))]

# ── Step 6: Build wiki index ────────────────────────────────────────────

def build_wiki_index(sessions, projects):
    keyword_map = {
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
    }
    
    projects_list = []
    for p in projects:
        p_sessions = [s for s in sessions if s.get("project") == p["name"]]
        p_sessions.sort(key=lambda x: x.get("started_at") or "", reverse=True)
        session_entries = [{
            "id": s["id"],
            "title": s.get("auto_title") or s.get("title") or "(untitled)",
            "summary": s.get("summary", ""),
            "date": s.get("date"),
            "source": s.get("source", ""),
        } for s in p_sessions]
        projects_list.append({
            "name": p["name"], "emoji": p["emoji"],
            "description": p["description"], "session_count": len(session_entries),
            "last_session": session_entries[0]["date"] if session_entries else None,
            "sessions": session_entries,
        })
    
    return {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "total_sessions": len(sessions),
        "total_projects": len(projects),
        "projects": projects_list,
        "quick_lookup": keyword_map,
    }

# ── Main ────────────────────────────────────────────────────────────────

def main():
    print("=== Rebuilding All Wiki Data ===\n")
    
    sessions = load_sessions()
    print(f"Sessions loaded: {len(sessions)}")
    
    projects = build_projects(sessions)
    print(f"Projects: {len(projects)}")
    
    daily_logs = build_daily_logs(sessions)
    print(f"Daily logs: {len(daily_logs)}")
    
    facts = build_facts(sessions)
    print(f"Facts: {len(facts)}")
    
    decisions = build_decisions(sessions)
    print(f"Decisions: {len(decisions)}")
    
    # Write all files
    with open(DATA_DIR / "sessions.json", "w") as f:
        json.dump(sessions, f, indent=2)
    
    with open(DATA_DIR / "projects.json", "w") as f:
        json.dump(projects, f, indent=2)
    
    with open(DATA_DIR / "daily_logs.json", "w") as f:
        json.dump(daily_logs, f, indent=2)
    
    with open(DATA_DIR / "facts.json", "w") as f:
        json.dump({"version": "1.0", "facts": facts}, f, indent=2)
    
    with open(DATA_DIR / "decisions.json", "w") as f:
        json.dump({"version": "1.0", "decisions": decisions}, f, indent=2)
    
    wiki_index = build_wiki_index(sessions, projects)
    with open(DATA_DIR / "wiki-index.json", "w") as f:
        json.dump(wiki_index, f, indent=2)
    
    print("\n=== All files written ===")
    print(f"sessions.json: {len(sessions)}")
    print(f"projects.json: {len(projects)}")
    print(f"daily_logs.json: {len(daily_logs)}")
    print(f"facts.json: {len(facts)}")
    print(f"decisions.json: {len(decisions)}")
    print(f"wiki-index.json: {wiki_index['total_sessions']} sessions, {wiki_index['total_projects']} projects")
    
    print("\n--- Projects ---")
    for p in projects:
        print(f"  {p['emoji']} {p['name']}: {p['session_count']}")
    
    print("\n--- Facts ---")
    for f in facts:
        print(f"  [{f['category']}] {f['fact'][:60]}")
    
    print("\n--- Decisions ---")
    for d in decisions:
        print(f"  {d['decision'][:60]}")

if __name__ == "__main__":
    main()
