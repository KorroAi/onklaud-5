#!/usr/bin/env python3
"""
Per-file code quality check - syntax (instant) + optional Kimi review (API).
Usage: python fast_gate.py <file.js> [file2.py ...] [--syntax-only] [--prompt "..."]
"""
import sys, os, json, subprocess

MY_DIR = os.path.dirname(os.path.abspath(__file__))
COUNCIL = os.path.join(MY_DIR, "council.py")

JS_EXTS = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
PY_EXTS = {".py", ".pyw"}

def check_syntax(filepath):
    """Instant syntax check using native tooling. Returns (ok, error_msg)."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in JS_EXTS:
            r = subprocess.run(["node", "--check", filepath], capture_output=True, text=True, timeout=10)
            return r.returncode == 0, r.stderr.strip() if r.stderr else ""
        elif ext in PY_EXTS:
            r = subprocess.run(["python", "-m", "py_compile", filepath], capture_output=True, text=True, timeout=10)
            return r.returncode == 0, r.stderr.strip() if r.stderr else ""
        else:
            return True, ""  # Unknown format, skip syntax check
    except Exception as e:
        return False, str(e)

def kimi_review(filepath, prompt=""):
    """Run Kimi review on a single file. Returns (score, passed, issues)."""
    prompt = prompt or "Review this code file for bugs, logic errors, and quality issues. Be thorough."
    r = subprocess.run(
        ["python", COUNCIL, "review", "--type", "code", "--prompt", prompt, "--draft-file", filepath],
        capture_output=True, text=True, timeout=120, cwd=MY_DIR
    )
    # council review outputs JSON to stdout on success
    try:
        result = json.loads(r.stdout)
        score = result.get("score", 0)
        passed = result.get("passed", False)
        issues = result.get("issues", [])
        critique = result.get("critique", "")
        return score, passed, issues, critique
    except json.JSONDecodeError:
        # Fallback: parse text output
        return 0, False, [r.stdout[:300]], ""

def main():
    syntax_only = False
    skip_kimi = False
    prompt = ""
    files = []

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--syntax-only":
            syntax_only = True
        elif a == "--skip-kimi":
            skip_kimi = True
        elif a == "--prompt" and i + 1 < len(args):
            i += 1
            prompt = args[i]
        else:
            files.append(a)
        i += 1

    if not files:
        print("Usage: python fast_gate.py <file.js> [file2.py ...] [--syntax-only] [--prompt ...]", file=sys.stderr)
        sys.exit(1)

    all_passed = True
    for fp in files:
        bn = os.path.basename(fp)
        # Step 1: Syntax check (always)
        ok, err = check_syntax(fp)
        if not ok:
            print(f"[SYNTAX] {bn}: FAIL - {err[:200]}")
            all_passed = False
            continue
        print(f"[SYNTAX] {bn}: OK")

        if syntax_only or skip_kimi:
            continue

        # Step 2: Kimi review
        score, passed, issues, critique = kimi_review(fp, prompt)
        status = "PASS" if passed else "FAIL"
        print(f"[KIMI] {bn}: {score}/10 {status}")
        if critique:
            print(f"  {critique[:300]}")
        if issues:
            for issue in issues[:5]:
                print(f"  [!] {issue}")
        if not passed:
            all_passed = False

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
