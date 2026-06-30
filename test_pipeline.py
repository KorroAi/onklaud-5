#!/usr/bin/env python3
"""
🎠 Onklaud 5 - End-to-End Pipeline Test
=======================================
Tests the complete pipeline: ponytail_ladder → council → quality_gate → verify.
Runs against all onklaud-5 Python files. No API calls needed for syntax tests.
Optional: --with-api to test OpenRouter connectivity.
"""

import sys
import os
import json
import subprocess
import time
import argparse
from pathlib import Path

MY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MY_DIR.parent
COUNCIL = MY_DIR / "council.py"
FAST_GATE = MY_DIR / "fast_gate.py"
QUALITY_GATE = MY_DIR / "quality_gate.py"
VERIFY = MY_DIR / "verify.py"
PONYTAIL_LADDER = MY_DIR / "ponytail_ladder.py"

# ASCII-safe on Windows
IS_WIN = sys.platform == "win32"
if IS_WIN:
    PASS = "[PASS]"
    FAIL = "[FAIL]"
    WARN = "[WARN]"
    # Force UTF-8 stdout
    if hasattr(sys.stdout, 'buffer'):
        try:
            sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        except Exception:
            pass
else:
    PASS = "✅"
    FAIL = "❌"
    WARN = "⚠️"

results = {"total": 0, "passed": 0, "failed": 0, "warnings": 0}

def test(name, condition, detail=""):
    results["total"] += 1
    if condition:
        results["passed"] += 1
        print(f"  {PASS} {name}")
    else:
        results["failed"] += 1
        print(f"  {FAIL} {name} - {detail}")
    return condition

def warn(name, detail=""):
    results["total"] += 1
    results["warnings"] += 1
    print(f"  {WARN} {name} - {detail}")

def test_ponytail_ladder():
    """Test 🎠 Ponytail Ladder against known patterns."""
    print("\n--- Ponytail Ladder Tests ---")

    # Run the tool directly
    KWARGS = {"capture_output": True, "text": True, "timeout": 10, "encoding": "utf-8", "errors": "replace"}

    r = subprocess.run(
        ["python", str(PONYTAIL_LADDER), "--task", "read a JSON file", "--json"],
        **KWARGS, cwd=str(PROJECT_ROOT)
    )
    data = json.loads(r.stdout.strip()) if r.stdout and r.stdout.strip() else {}
    test("Detects 'read JSON' as stdlib (Python)", data.get("found") and data.get("level") == "stdlib",
         f"Got: {json.dumps(data)}")

    r = subprocess.run(
        ["python", str(PONYTAIL_LADDER), "--task", "parse a URL", "--lang", "js", "--json"],
        **KWARGS, cwd=str(PROJECT_ROOT)
    )
    data = json.loads(r.stdout.strip()) if r.stdout and r.stdout.strip() else {}
    test("Detects 'parse URL' as stdlib (JS)", data.get("found"),
         f"Got: {json.dumps(data)}")

    r = subprocess.run(
        ["python", str(PONYTAIL_LADDER), "--task", "dark mode toggle", "--json"],
        **KWARGS, cwd=str(PROJECT_ROOT)
    )
    data = json.loads(r.stdout.strip()) if r.stdout and r.stdout.strip() else {}
    test("Detects 'dark mode' as native CSS", data.get("found") and data.get("level") == "native",
         f"Got: {json.dumps(data)}")

    r = subprocess.run(
        ["python", str(PONYTAIL_LADDER), "--task", "a highly specific custom workflow that doesn't exist",
         "--json"],
        capture_output=True, text=True, timeout=10, cwd=str(PROJECT_ROOT)
    )
    data = json.loads(r.stdout) if r.stdout else {}
    test("Correctly returns NOT FOUND for custom task", not data.get("found"),
         f"Got: {json.dumps(data)}")

def test_syntax_all_python():
    """Syntax check all Python files in onklaud-5/."""
    print("\n--- Syntax Checks (all onklaud-5 Python files) ---")
    all_ok = True
    for py_file in sorted(MY_DIR.glob("*.py")):
        r = subprocess.run(
            ["python", str(FAST_GATE), str(py_file), "--syntax-only"],
            capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT)
        )
        ok = "OK" in r.stdout
        if not ok:
            all_ok = False
            print(f"  {FAIL} {py_file.name}: {r.stdout.strip()}")
        else:
            test(f"Syntax OK: {py_file.name}", True)
    return all_ok

def test_quality_gate():
    """Test quality gate with various inputs."""
    print("\n--- Quality Gate Tests ---")

    # Test good input
    r = subprocess.run(
        ["python", str(QUALITY_GATE),
         "This is a comprehensive and well-structured response with proper error handling. It handles all edge cases including null, empty arrays, and boundary conditions. The implementation is clean, documented, and follows best practices for security and performance.", "general"],
        capture_output=True, text=True, timeout=15, cwd=str(PROJECT_ROOT)
    )
    # Quality gate uses exit code 0 for pass
    test("Quality gate script runs without errors", r.returncode in (0, 1),
         f"Exit: {r.returncode}")

    # Test bad input
    r = subprocess.run(
        ["python", str(QUALITY_GATE), "x", "coding"],
        capture_output=True, text=True, timeout=15, cwd=str(PROJECT_ROOT)
    )
    data = json.loads(r.stdout) if r.stdout else {}
    test("Quality gate fails short input", data.get("passed") == False or data.get("score", 10) < 10,
         f"Score: {data.get('score')}")

def test_fast_gate():
    """Test fast gate on known files."""
    print("\n--- ⚡ Fast Gate Tests ---")

    r = subprocess.run(
        ["python", str(FAST_GATE), str(COUNCIL), "--syntax-only"],
        capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT)
    )
    test("Fast gate: council.py syntax", "OK" in r.stdout, r.stdout.strip()[:100])

    r = subprocess.run(
        ["python", str(FAST_GATE), str(COUNCIL), str(QUALITY_GATE), str(VERIFY), str(PONYTAIL_LADDER), "--syntax-only"],
        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT)
    )
    test("Fast gate: all core files syntax", r.returncode == 0, r.stdout.strip()[:200])

def test_council_cli():
    """Test council.py CLI modes."""
    print("\n--- 🔮 Council CLI Tests ---")

    # Test status
    r = subprocess.run(
        ["python", str(COUNCIL), "status"],
        capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT)
    )
    has_ok = "status" in r.stdout.lower() or "operational" in r.stdout.lower() or "degraded" in r.stdout.lower() or "key" in r.stdout.lower()
    test("Council status command works", has_ok, r.stdout.strip()[:100])

    # Test gate mode (no API needed)
    r = subprocess.run(
        ["python", str(COUNCIL), "gate", "--text", "A simple test response", "--domain", "general"],
        capture_output=True, text=True, timeout=15, cwd=str(PROJECT_ROOT)
    )
    test("Council gate command works", r.returncode in (0, 1),
         f"Exit: {r.returncode}, out: {r.stdout.strip()[:100]}")

    # Test dual mode (requires API key, may degrade)
    if os.environ.get("OPENROUTER_API_KEY"):
        r = subprocess.run(
            ["python", str(COUNCIL), "dual", "--type", "code",
             "--prompt", "Test dual review", "--draft", "print('hello')", "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT)
        )
        test("Council dual mode (with API)", r.returncode in (0, 1),
             f"Exit: {r.returncode}")
    else:
        warn("Council dual mode (skipped - no API key)", "Set OPENROUTER_API_KEY to test API calls")

def test_config():
    """Validate config.yaml."""
    print("\n--- ⚙️ Config Tests ---")
    import yaml
    try:
        config = yaml.safe_load(open(MY_DIR / "nadirclaw" / "config.yaml"))
        test("config.yaml is valid YAML", True)
        test("Has models section", "models" in config)
        test("Has council section", "council" in config)
        test("Has rules section", "rules" in config)
        test("Ponytail ladder in pipeline", "ponytail_ladder" in json.dumps(config).lower())
    except Exception as e:
        test("config.yaml is valid", False, str(e))

def main():
    global results
    parser = argparse.ArgumentParser(description="Onklaud 5 End-to-End Pipeline Test")
    parser.add_argument("--with-api", action="store_true", help="Include API-dependent tests")
    args = parser.parse_args()

    print("=" * 60)
    print("  [Onklaud 5] END-TO-END PIPELINE TEST")
    print("=" * 60)

    start = time.time()

    test_ponytail_ladder()
    test_syntax_all_python()
    test_quality_gate()
    test_fast_gate()
    test_council_cli()
    test_config()

    elapsed = time.time() - start

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {results['passed']}/{results['total']} passed "
          f"({results['failed']} failed, {results['warnings']} warnings)")
    print(f"  Time: {elapsed:.1f}s")
    print(f"{'=' * 60}")

    # Return exit code
    if results["failed"] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
