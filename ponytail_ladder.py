#!/usr/bin/env python3
"""
🎠 Ponytail Ladder - checks if a task can be solved with stdlib/native/existing-dep.
Returns the shortest solution that works. Zero API calls. Instant.

Usage:
  python onklaud-5/ponytail_ladder.py --task "read a JSON file in Python"
  python onklaud-5/ponytail_ladder.py --task "parse URL query string in JavaScript" --lang js
  python onklaud-5/ponytail_ladder.py --task "add dark mode toggle" --project-dir /path/to/project

Output:
  {"found": true, "level": "stdlib", "solution": "import json; json.load(path)", "language": "python"}
  {"found": false, "reason": "Requires custom implementation", "suggestion": "..."}

Exit codes: 0 = found (stdlib/native/dep covers it), 1 = not found (needs custom code)
"""

import sys
import os
import json
import argparse
import re
from pathlib import Path

# --- Knowledge Base ---------------------------------------------------

# Pattern -> solution mapping for common tasks
STDLIB_PATTERNS = {
    # Python
    "python": {
        "read json": "import json; data = json.load(open(path))",
        "write json": "import json; json.dump(data, open(path, 'w'))",
        "read csv": "import csv; rows = list(csv.DictReader(open(path)))",
        "http get": "import urllib.request; data = urllib.request.urlopen(url).read()",
        "parse url": "from urllib.parse import urlparse; parsed = urlparse(url)",
        "parse date": "from datetime import datetime; dt = datetime.fromisoformat(s)",
        "format date": "from datetime import datetime; s = dt.strftime('%Y-%m-%d')",
        "date formatter": "from datetime import datetime; s = dt.isoformat()",
        "generate uuid": "import uuid; id = str(uuid.uuid4())",
        "hash file": "import hashlib; h = hashlib.sha256(open(path,'rb').read()).hexdigest()",
        "temp file": "import tempfile; with tempfile.NamedTemporaryFile() as f: pass",
        "run command": "import subprocess; result = subprocess.run(['cmd'], capture_output=True, text=True)",
        "walk directory": "import pathlib; for f in pathlib.Path(dir).rglob('*'): print(f)",
        "environment variable": "import os; val = os.environ.get('KEY', 'default')",
        "sleep seconds": "import time; time.sleep(seconds)",
        "delay execution": "import time; time.sleep(seconds)",
        "random number": "import random; n = random.randint(1, 100)",
        "base64 encode": "import base64; encoded = base64.b64encode(data).decode()",
        "zip archive": "import zipfile; with zipfile.ZipFile(path) as z: z.extractall(dir)",
        "unzip extract": "import zipfile; with zipfile.ZipFile(path) as z: z.extractall(dir)",
        "regex match": "import re; m = re.search(pattern, text)",
        "log message": "import logging; logging.basicConfig(level=logging.INFO); logging.info(msg)",
        "config file": "import configparser; cfg = configparser.ConfigParser(); cfg.read(path)",
    },
    # JavaScript/TypeScript
    "js": {
        "read file": "import { readFileSync } from 'node:fs'; const data = readFileSync(path, 'utf-8')",
        "write file": "import { writeFileSync } from 'node:fs'; writeFileSync(path, data)",
        "read json": "import { readFileSync } from 'node:fs'; const obj = JSON.parse(readFileSync(path, 'utf-8'))",
        "parse url": "const url = new URL(input); // url.pathname, url.searchParams",
        "http get": "const data = await fetch(url).then(r => r.json())",
        "generate uuid": "import { randomUUID } from 'node:crypto'; const id = randomUUID()",
        "hash string": "import { createHash } from 'node:crypto'; const h = createHash('sha256').update(s).digest('hex')",
        "sleep/delay": "await new Promise(r => setTimeout(r, ms))",
        "environment variable": "const val = process.env.KEY || 'default'",
        "path join": "import { join } from 'node:path'; const full = join(dir, file)",
        "temp dir": "import { mkdtempSync } from 'node:fs'; import { tmpdir } from 'node:os'; const dir = mkdtempSync(join(tmpdir(), 'prefix-'))",
        "parse date": "const d = new Date(isoString); // or new Date() for now",
        "regex match": "const m = /pattern/.exec(text)",
        "base64 encode": "const encoded = Buffer.from(data).toString('base64')",
    },
}

# Native HTML/CSS patterns that don't need any code at all
NATIVE_PATTERNS = {
    "date picker": "<input type=\"date\"> - native date picker, no JS needed",
    "color picker": "<input type=\"color\"> - native color picker",
    "form validation": "<input required pattern=\"[a-z]+\" minlength=\"2\" maxlength=\"50\"> - HTML5 validation, no JS",
    "dropdown": "<select><option>...</option></select> - native dropdown",
    "number input": "<input type=\"number\" min=\"0\" max=\"100\" step=\"1\">",
    "file upload": "<input type=\"file\" accept=\".pdf,.jpg\" multiple>",
    "range slider": "<input type=\"range\" min=\"0\" max=\"100\">",
    "progress bar": "<progress value=\"50\" max=\"100\"></progress>",
    "dark mode": "@media (prefers-color-scheme: dark) { ... } - no JS, CSS handles it",
    "responsive layout": "CSS grid/flexbox - @media queries, no JS",
    "smooth scroll": "scroll-behavior: smooth; - CSS property, no JS",
    "sticky header": "position: sticky; top: 0; - CSS, no JS",
    "animations": "@keyframes + animation - CSS animations, no JS needed for simple ones",
    "tooltip": "[title=\"hover text\"] - native tooltip attribute",
    "details/summary": "<details><summary>Title</summary>Content</details> - native expandable",
    "dialog/modal": "<dialog> - native modal, .showModal() if JS needed",
}

def detect_language(task, project_dir=None):
    """Detect language from task description and project files."""
    task_lower = task.lower()

    # Explicit language mention
    if any(kw in task_lower for kw in ["python", ".py", "django", "flask", "fastapi"]):
        return "python"
    if any(kw in task_lower for kw in ["javascript", "typescript", "node", "react", "next", "vue", "angular",
                                        ".js", ".ts", ".jsx", ".tsx", "npm", "vite", "express"]):
        return "js"

    # Check project files
    if project_dir:
        root = Path(project_dir)
        if (root / "package.json").exists():
            return "js"
        if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            return "python"

    # Default
    return "python"

def check_stdlib(task, lang):
    """Check if task matches a stdlib pattern."""
    if lang not in STDLIB_PATTERNS:
        return None

    patterns = STDLIB_PATTERNS[lang]
    task_lower = task.lower()
    task_words = set(task_lower.split())

    for pattern, solution in patterns.items():
        pattern_words = set(pattern.split())
        # All pattern words must appear in task words
        if pattern_words.issubset(task_words):
            return {"level": "stdlib", "solution": solution, "language": lang, "pattern_matched": pattern}

    return None

def check_native(task):
    """Check if task can be solved with native HTML/CSS."""
    task_lower = task.lower()
    task_words = set(task_lower.split())
    for pattern, solution in NATIVE_PATTERNS.items():
        pattern_words = set(pattern.split())
        if pattern_words.issubset(task_words):
            return {"level": "native", "solution": solution, "pattern_matched": pattern}

    return None

def check_existing_dep(task, project_dir=None):
    """Check if project already has a dependency that covers this."""
    if not project_dir or not os.path.isdir(project_dir):
        return None

    root = Path(project_dir)

    # Check Node.js dependencies
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {}
            deps.update(pkg.get("dependencies", {}))
            deps.update(pkg.get("devDependencies", {}))
            task_lower = task.lower()

            dep_mappings = {
                "lodash": ["filter", "map", "debounce", "throttle", "merge", "clone", "group"],
                "axios": ["http", "api call", "fetch", "request"],
                "date-fns": ["date format", "date parse", "date diff"],
                "zod": ["validate", "schema", "type check"],
                "express": ["server", "route", "middleware"],
                "react": ["component", "hook", "state"],
                "next": ["page", "route", "ssr"],
                "tailwind": ["style", "css", "layout"],
                "prisma": ["database", "query", "orm", "migrate"],
                "zod": ["validate", "schema", "type check"],
            }

            for dep_name, keywords in dep_mappings.items():
                if dep_name in deps and any(kw in task_lower for kw in keywords):
                    return {
                        "level": "existing_dep",
                        "dep": dep_name,
                        "version": deps[dep_name],
                    }
        except Exception:
            pass

    # Check Python dependencies
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        try:
            reqs = req_txt.read_text(encoding="utf-8")
            task_lower = task.lower()

            py_dep_mappings = {
                "requests": ["http", "api call", "fetch", "request"],
                "pydantic": ["validate", "schema", "type check"],
                "fastapi": ["server", "route", "api"],
                "sqlalchemy": ["database", "query", "orm"],
                "click": ["cli", "command line"],
                "rich": ["console", "terminal", "progress"],
                "httpx": ["http", "async request"],
                "pytest": ["test", "assert"],
            }

            for dep_name, keywords in py_dep_mappings.items():
                if dep_name.lower() in reqs.lower() and any(kw in task_lower for kw in keywords):
                    return {
                        "level": "existing_dep",
                        "dep": dep_name,
                    }
        except Exception:
            pass

    return None

def run_ladder(task, project_dir=None, lang=None):
    """Run the full Ponytail ladder. Returns (result, exit_code)."""
    if not lang:
        lang = detect_language(task, project_dir)

    # Step 1: Stdlib
    result = check_stdlib(task, lang)
    if result:
        result["found"] = True
        return result, 0

    # Step 2: Native platform
    result = check_native(task)
    if result:
        result["found"] = True
        return result, 0

    # Step 3: Existing dependency
    if project_dir:
        result = check_existing_dep(task, project_dir)
        if result:
            result["found"] = True
            return result, 0

    # Step 4: Not found - needs custom code
    return {
        "found": False,
        "reason": "Task requires custom implementation",
        "suggestion": "Use shortest possible implementation: 1 line > 1 function > 1 file > 1 module",
        "language": lang,
    }, 1

def main():
    parser = argparse.ArgumentParser(
        description="🎠 Ponytail Ladder - check if task can be solved with stdlib/native/existing-dep"
    )
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--lang", choices=["python", "js"], help="Language (auto-detected if omitted)")
    parser.add_argument("--project-dir", help="Project directory to check existing deps")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    result, code = run_ladder(args.task, args.project_dir, args.lang)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["found"]:
            level = result.get("level", "???")
            solution = result.get("solution", "")
            print(f"🎠 FOUND ({level}): {solution}")
        else:
            print(f"🎠 NOT FOUND: {result.get('reason', '')}")
            print(f"   {result.get('suggestion', '')}")

    sys.exit(code)

if __name__ == "__main__":
    main()
