#!/usr/bin/env python3
"""
rebuild_facts_decisions.py — Rebuild facts.json and decisions.json from session summaries.
Only extracts clean factual statements about the user's environment, tools, preferences.
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def is_meta_sentence(text):
    """Check if a sentence is meta-analysis of the session itself."""
    text_lower = text.lower().strip()
    meta_patterns = [
        r"^no (code|files?|work|output|synthesis|final|meaningful|substantive|actual|video|implementation)",
        r"^the (session|conversation|task|excerpt|interaction|request) (was|is|ended|began)",
        r"^(this|the) (session|conversation|excerpt|interaction)",
        r"^key (takeaway|takeaways) (include|includes)",
        r"^(the user|user|the assistant|owl) (requested|asked|initiated|sent|began|started|noted|provided)",
        r"^on \w+ \d+,",  # date references
        r"^---", r"^\[", r"^>",
        r"^all existing functionality",
        r"^no (outcomes?|deliverables?|results?)",
        r"^there were no",
        r"^the (rules?|workflow|process|methodology)",
        r"^owl (surveyed|checked|began|started|attempted)",
        r"^the assistant (began|started|attempted|provided|responded)",
        r"^for the (computer|setup|question)",
        r"^he provided",
        r"^they (requested|also|wanted)",
        r"^no (tools?|files?|code) (were|was)",
    ]
    for pattern in meta_patterns:
        if re.match(pattern, text_lower):
            return True
    return False

def is_factual(text):
    """Check if a sentence contains factual information about the user/project."""
    text_lower = text.lower()
    # Must contain at least one factual keyword
    factual_keywords = [
        # Environment
        "mac", "computer", "machine", "device", "os", "port", "server", "deployed", "localhost",
        "running on", "hosted on", "macos", "ubuntu", "windows",
        # Tools
        "next.js", "react", "tailwind", "python", "docker", "vercel", "github", "typescript",
        "javascript", "node", "mcp", "cli", "api", "database", "postgresql", "sqlite",
        "framework", "library", "package", "tool", "software",
        # Preferences
        "prefers", "always", "never", "usually", "likes", "style", "theme", "dark", "light",
        "concise", "brief", "technical", "helpful",
        # Conventions
        "convention", "pattern", "standard", "workflow", "process", "branch", "pr", "review",
        # Constraints
        "cannot", "can't", "must", "limit", "avoid", "constraint", "restrict", "port",
    ]
    return any(k in text_lower for k in factual_keywords)

def classify_fact(text):
    text_lower = text.lower()
    if any(k in text_lower for k in ["mac", "computer", "machine", "device", "os", "port", "server", "deployed", "localhost", "running on", "hosted on"]):
        return "environment"
    if any(k in text_lower for k in ["next.js", "react", "tailwind", "python", "docker", "vercel", "github", "typescript", "javascript", "node", "mcp", "cli", "api", "database", "framework", "library", "package", "tool", "software"]):
        return "tools"
    if any(k in text_lower for k in ["prefers", "always", "never", "usually", "likes", "style", "theme", "dark", "light", "concise", "brief", "technical", "helpful"]):
        return "preferences"
    if any(k in text_lower for k in ["convention", "pattern", "standard", "workflow", "process", "branch", "pr", "review"]):
        return "conventions"
    if any(k in text_lower for k in ["cannot", "can't", "must", "limit", "avoid", "constraint", "restrict"]):
        return "constraints"
    return "preferences"

def main():
    print("=== Rebuilding facts and decisions ===\n")
    
    sessions = json.load(open(DATA_DIR / "sessions.json"))
    print(f"Sessions: {len(sessions)}")
    
    all_facts = {}
    all_decisions = {}
    
    for s in sessions:
        sid = s["id"]
        summary = s.get("summary", "") or ""
        if not summary or len(summary) < 20:
            continue
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        for sent in sentences:
            sent = sent.strip().strip('"').strip()
            if len(sent) < 15 or len(sent) > 200:
                continue
            # Skip meta sentences
            if is_meta_sentence(sent):
                continue
            # Only keep factual sentences
            if not is_factual(sent):
                continue
            
            cat = classify_fact(sent)
            key = re.sub(r'\s+', ' ', sent.lower())[:60]
            if key not in all_facts:
                all_facts[key] = {"fact": sent, "category": cat, "sessions": [sid]}
        
        # Extract decisions
        for match in re.finditer(r"(?:the user|user)\s+(?:decided|chose|specified)\s+(?:to\s+)?([^.]+)", summary, re.IGNORECASE):
            text = match.group(0).strip()
            if len(text) > 15:
                key = re.sub(r'\s+', ' ', text.lower())[:60]
                if key not in all_decisions:
                    all_decisions[key] = {"decision": text, "sessions": [sid]}
    
    # Write facts
    facts_list = [{"id": f"fact_{i+1:03d}", **v} for i, v in enumerate(sorted(all_facts.values(), key=lambda x: (x["category"], x["fact"])))]
    with open(DATA_DIR / "facts.json", "w") as f:
        json.dump({"version": "1.0", "facts": facts_list}, f, indent=2)
    print(f"Facts: {len(facts_list)}")
    
    # Write decisions
    decisions_list = [{"id": f"dec_{i+1:03d}", **v} for i, v in enumerate(sorted(all_decisions.values(), key=lambda x: x["decision"]))]
    with open(DATA_DIR / "decisions.json", "w") as f:
        json.dump({"version": "1.0", "decisions": decisions_list}, f, indent=2)
    print(f"Decisions: {len(decisions_list)}")
    
    print("\n--- Facts ---")
    for f in facts_list:
        print(f"  [{f['category']}] {f['fact'][:70]}")
    print("\n--- Decisions ---")
    for d in decisions_list:
        print(f"  {d['decision'][:70]}")

if __name__ == "__main__":
    main()
