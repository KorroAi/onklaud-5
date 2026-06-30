#!/usr/bin/env python3
"""
🔮 Onklaud 5 Pre-Check - scans immune memory BEFORE generating code.
Prevents repeating past failures. Zero API calls. Instant.

Usage:
  python onklaud-5/pre_check.py --task "write an HTTP retry function"
  python onklaud-5/pre_check.py --file src/api.ts --json

Output:
  {"warnings": [{"pattern": "...", "frequency": 3, "match": "retry loop"}], "score": "clean|warning|danger"}
"""

import sys
import os
import json
import re
from pathlib import Path
from difflib import SequenceMatcher

SCRIPT_DIR = Path(__file__).resolve().parent
IMMUNE_FILE = SCRIPT_DIR / "immune_memory.json"

# Known failure categories for fuzzy matching
FAILURE_CATEGORIES = {
    "retry": ["retry", "backoff", "rate limit", "429", "circuit breaker"],
    "type_safety": ["unknown", "any type", "null assertion", "non-null", "as T", "cast"],
    "cleanup": ["cancel", "cleanup", "dispose", "abort", "flush", "memory leak"],
    "race_condition": ["race", "concurrent", "deadlock", "atomic", "lock"],
    "magic_numbers": ["magic number", "hardcode", "16000", "12000", "constant"],
    "error_handling": ["try catch", "error", "exception", "throw", "panic"],
    "api_design": ["API", "endpoint", "interface", "contract", "breaking"],
    "validation": ["validate", "sanitize", "input", "schema", "parse"],
}

def load_memory():
    if not IMMUNE_FILE.exists():
        return []
    try:
        return json.loads(IMMUNE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def fuzzy_match(text, pattern, threshold=0.4):
    """Check if text is similar to a pattern."""
    # Word overlap
    text_words = set(re.findall(r'\w+', text.lower()))
    pattern_words = set(re.findall(r'\w+', pattern.lower()))
    if not pattern_words:
        return 0.0
    overlap = len(text_words & pattern_words) / len(pattern_words)
    return overlap

def check_task(task_description):
    """Check a task description against immune memory."""
    memories = load_memory()
    if not memories:
        return {"warnings": [], "relevant": [], "score": "clean", "total_patterns": 0}

    warnings = []
    relevant = []

    for mem in memories:
        pattern = mem.get("pattern", "")
        freq = mem.get("frequency", 1)

        # Fuzzy match task against pattern
        similarity = fuzzy_match(task_description, pattern)
        if similarity > 0.3:
            relevant.append({
                "pattern_preview": pattern[:120],
                "frequency": freq,
                "similarity": round(similarity, 2),
                "last_seen": mem.get("last_seen", "unknown"),
            })

        # Category-based matching
        task_lower = task_description.lower()
        for category, keywords in FAILURE_CATEGORIES.items():
            if any(kw in task_lower for kw in keywords):
                # Check if any memory matches this category
                pattern_lower = pattern.lower()
                if any(kw in pattern_lower for kw in keywords):
                    warnings.append({
                        "category": category,
                        "pattern_preview": pattern[:150],
                        "frequency": freq,
                    })
                    break

    # Deduplicate warnings by category
    seen = set()
    unique_warnings = []
    for w in warnings:
        if w["category"] not in seen:
            seen.add(w["category"])
            unique_warnings.append(w)

    score = "clean"
    if len(unique_warnings) >= 3:
        score = "danger"
    elif len(unique_warnings) >= 1:
        score = "warning"

    return {
        "warnings": unique_warnings,
        "relevant": relevant[:5],
        "score": score,
        "total_patterns": len(memories),
    }

def check_file(filepath):
    """Check a code file against immune memory patterns."""
    if not os.path.isfile(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)}

    return check_task(content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Onklaud 5 Pre-Check - scan immune memory before coding")
    parser.add_argument("--task", help="Task description to check")
    parser.add_argument("--file", help="Code file to check against patterns")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.file:
        result = check_file(args.file)
    elif args.task:
        result = check_task(args.task)
    else:
        # Read from stdin
        if not sys.stdin.isatty():
            result = check_task(sys.stdin.read())
        else:
            print("Error: provide --task, --file, or stdin", file=sys.stderr)
            sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("score") == "clean" else 1)

if __name__ == "__main__":
    main()
