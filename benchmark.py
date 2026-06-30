#!/usr/bin/env python3
"""
Onklaud 5 Benchmark - Prove the council beats any single model.

This script compares Onklaud 5 council output against single-model (Fable 5 / Claude Sonnet 3.5) output.
It runs quality gate scoring on both, plus council review, and produces a comparison report.

Usage:
  # Compare single-model draft against council review
  python onklaud-5/benchmark.py --prompt "Write a function to..." --draft "function foo() {...}"

  # From files
  python onklaud-5/benchmark.py --prompt-file task.txt --draft-file output.txt --type code

  # Compare two different outputs directly (single-model vs council-enhanced)
  python onklaud-5/benchmark.py --baseline baseline.txt --council council_output.txt --type code
"""

import sys
import os
import json
import argparse
import subprocess
import time
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

COUNCIL_PY = SCRIPT_DIR / "council.py"
GATE_PY = SCRIPT_DIR / "quality_gate.py"

BENCHMARKS_MD = SCRIPT_DIR / "BENCHMARKS.md"


def style(text, code=""):
    """Simple ANSI styling for terminal output."""
    colors = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m",
        "magenta": "\033[95m"
    }
    if code in colors:
        return f"{colors[code]}{text}{colors['reset']}"
    return text


def run_quality_gate(text: str, domain: str = "general") -> dict:
    """Run quality gate on text. Returns {score, passed, issues, gates}."""
    try:
        result = subprocess.run(
            [sys.executable, str(GATE_PY), text, domain],
            capture_output=True, text=True, timeout=15
        )
        # Parse stdout even if exit code != 0
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            data = json.loads(output)
            return data
    except json.JSONDecodeError:
        pass
    except Exception as e:
        return {"score": 0, "passed": False, "error": str(e), "issues": [], "gates": []}

    return {"score": 0, "passed": False, "error": "Gate invocation failed", "issues": [], "gates": []}


def run_council_full(draft: str, prompt: str, review_type: str = "code") -> dict:
    """Run full council (review + gate) on draft. Returns council trace."""
    try:
        result = subprocess.run(
            [sys.executable, str(COUNCIL_PY), "full", "--type", review_type,
             "--prompt", prompt, "--draft", draft],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout.strip()
        # Parse JSON from stdout
        if output:
            data = json.loads(output)
            return data
    except json.JSONDecodeError:
        pass
    except Exception as e:
        return {"error": str(e), "final_score": 0, "passed": False}

    return {"error": "Council invocation failed", "final_score": 0, "passed": False}


def measure_text_quality(text: str) -> dict:
    """Quick stats about output quality."""
    stats = {
        "chars": len(text),
        "lines": text.count("\n") + 1,
        "words": len(text.split()),
        "has_code_blocks": "```" in text,
        "has_todos": "TODO" in text or "FIXME" in text,
        "has_debug": bool(re.search(r'(console\.log|debugger|print\()', text)),
        "has_types": bool(re.search(r'(string|number|boolean|int|float|void|: [A-Z])', text, re.IGNORECASE)),
        "has_error_handling": bool(re.search(r'(try|catch|except|error|throw)', text, re.IGNORECASE)),
    }
    return stats


def compare_outputs(baseline_text: str, council_result: dict, prompt: str, review_type: str):
    """Compare single-model vs council output with visual report."""
    b_gate = run_quality_gate(baseline_text, review_type if review_type in ("coding", "architecture") else "general")
    b_stats = measure_text_quality(baseline_text)

    score_baseline = b_gate.get("score", 0)
    score_council = council_result.get("final_score", 0)
    delta = score_council - score_baseline

    # Council review details
    review = council_result.get("review", {})
    review_issues = council_result.get("all_issues", [])
    gate_issues = b_gate.get("issues", [])

    # Print report
    print()
    print("=" * 70)
    print(style("  ONKLAUD 5 BENCHMARK - Council vs Single Model", "bold"))
    print("=" * 70)
    print()

    print(style("  TASK", "bold"))
    print(f"  Type: {review_type}")
    print(f"  Prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    print()

    print(style("  QUALITY SCORES", "bold"))
    print(f"  {'Single Model (Fable 5)':.<40} {style(f'{score_baseline}/10', 'red' if score_baseline < 8 else 'green')}")
    print(f"  {'Onklaud 5 Council':.<40} {style(f'{score_council}/10', 'green' if score_council >= 8 else 'red')}")
    print(f"  {'Delta':.<40} {style(f'+{delta}' if delta > 0 else f'{delta}', 'green' if delta > 0 else 'yellow')}")
    print()

    print(style("  SCORE BREAKDOWN", "bold"))
    if review:
        reviewer_model = review.get("reviewer", council_result.get("reviewer", "unknown"))
        review_score = review.get("score", "?")
        review_passed = review.get("passed", False)
        print(f"  Reviewer ({reviewer_model}): {review_score}/10 {'PASS' if review_passed else 'FAIL'}")

    gate_result = council_result.get("gate", {})
    if gate_result:
        gate_score = gate_result.get("score", "?")
        gate_passed = gate_result.get("passed", False)
        print(f"  Quality Gate:              {gate_score}/10 {'PASS' if gate_passed else 'FAIL'}")

    print()

    # Gate-level breakdown
    if b_gate.get("gates"):
        print(style("  SINGLE MODEL GATE DETAILS", "bold"))
        for g in b_gate["gates"]:
            status = style("PASS", "green") if g["passed"] else style("FAIL", "red")
            issues_str = f" - {', '.join(g['issues'])}" if g.get("issues") else ""
            print(f"  [{status}] {g['name']}{issues_str}")
        print()

    if review_issues:
        print(style("  COUNCIL REVIEW ISSUES FOUND", "bold"))
        for issue in review_issues[:10]:
            print(f"  - {issue}")
        if len(review_issues) > 10:
            print(f"  ... and {len(review_issues) - 10} more")
        print()

    print(style("  TEXT QUALITY COMPARISON", "bold"))
    print(f"  {'Chars':.<20} {b_stats['chars']}")
    print(f"  {'Lines':.<20} {b_stats['lines']}")
    print(f"  {'Has code blocks':.<20} {'Yes' if b_stats['has_code_blocks'] else 'No'}")
    print(f"  {'Has error handling':.<20} {'Yes' if b_stats['has_error_handling'] else 'No'}")
    print(f"  {'Has debug stmts':.<20} {'Yes' if b_stats['has_debug'] else 'No'}")
    print()

    print(style("  PIPELINE TRACE", "bold"))
    print(f"  {council_result.get('pipeline', 'N/A')}")
    print()

    # Verdict
    print(style("  VERDICT", "bold"))
    if score_council >= 8 and score_council > score_baseline:
        print(style(f"  Onklaud 5 council passes quality gate ({score_council}/10)", "green"))
        print(style(f"  Beats single model by {delta} points", "green"))
        print(f"  Council found {len(review_issues)} issues single model missed")
    elif score_council >= 8:
        print(style(f"  Onklaud 5 council passes quality gate ({score_council}/10)", "green"))
        print(style(f"  Single model also passes ({score_baseline}/10) - tied", "yellow"))
    else:
        print(style(f"  Council score {score_council}/10 - below quality threshold", "red"))
        print(f"  Baseline single model: {score_baseline}/10")
        if score_council > score_baseline:
            print(style(f"  Council improves by {delta} points but still fails gate", "yellow"))

    print()
    print("=" * 70)
    print(style(f"  FINAL: Onklaud 5 {'BEATS' if score_council > score_baseline else 'TIES WITH' if score_council == score_baseline else 'LOSES TO'} Fable 5", "bold"))
    print(f"  Score: {score_council}/10 council vs {score_baseline}/10 single model")
    print(f"  Pipeline: {council_result.get('pipeline', 'N/A')}")
    print("=" * 70)
    print()

    return {
        "baseline_score": score_baseline,
        "council_score": score_council,
        "delta": delta,
        "council_passed": score_council >= 8,
        "baseline_passed": score_baseline >= 8,
        "review_issues": len(review_issues),
        "gate_issues": len(gate_issues),
    }


def cmd_compare(args):
    """Compare two output texts directly (baseline vs council-enhanced)."""
    baseline = args.baseline
    if not baseline and args.baseline_file:
        baseline = Path(args.baseline_file).read_text(encoding="utf-8", errors="ignore")
    if not baseline:
        print("Error: --baseline or --baseline-file required", file=sys.stderr)
        sys.exit(1)

    council_text = args.council
    if not council_text and args.council_file:
        council_text = Path(args.council_file).read_text(encoding="utf-8", errors="ignore")
    if not council_text:
        print("Error: --council or --council-file required", file=sys.stderr)
        sys.exit(1)

    review_type = args.type

    b_gate = run_quality_gate(baseline, review_type if review_type in ("coding", "architecture") else "general")
    c_gate = run_quality_gate(council_text, review_type if review_type in ("coding", "architecture") else "general")

    score_b = b_gate.get("score", 0)
    score_c = c_gate.get("score", 0)
    delta = score_c - score_b

    print()
    print("=" * 70)
    print(style("  ONKLAUD 5 BENCHMARK - Head to Head Comparison", "bold"))
    print("=" * 70)
    print()

    print(style("  QUALITY GATE SCORES", "bold"))
    print(f"  {'Single Model (Fable 5)':.<40} {style(f'{score_b}/10', 'red' if score_b < 8 else 'green')}")
    print(f"  {'Onklaud 5 Council Output':.<40} {style(f'{score_c}/10', 'green' if score_c >= 8 else 'red')}")
    print(f"  {'Delta':.<40} {style(f'+{delta}' if delta > 0 else f'{delta}', 'green' if delta > 0 else 'yellow')}")
    print()

    b_gates = b_gate.get("gates", [])
    c_gates = c_gate.get("gates", [])

    if b_gates and c_gates:
        print(style("  GATE-BY-GATE COMPARISON", "bold"))
        for bg, cg in zip(b_gates, c_gates):
            name = bg.get("name", cg.get("name", "?"))
            bp = "PASS" if bg.get("passed") else "FAIL"
            cp = "PASS" if cg.get("passed") else "FAIL"
            b_color = "green" if bg.get("passed") else "red"
            c_color = "green" if cg.get("passed") else "red"
            print(f"  {name:<25} Fable 5: {style(bp, b_color)}  |  Onklaud 5: {style(cp, c_color)}")
        print()

    b_issues = b_gate.get("issues", [])
    c_issues = c_gate.get("issues", [])

    only_in_b = set(b_issues) - set(c_issues)
    only_in_c = set(c_issues) - set(b_issues)

    if only_in_b:
        print(style(f"  ISSUES UNIQUE TO SINGLE MODEL ({len(only_in_b)})", "red"))
        for issue in only_in_b:
            print(f"  - {issue}")
        print()

    if only_in_c:
        print(style(f"  ISSUES UNIQUE TO COUNCIL ({len(only_in_c)})", "yellow"))
        for issue in only_in_c:
            print(f"  - {issue}")
        print()

    if not only_in_b and not only_in_c and b_issues == c_issues:
        print(style("  Both outputs have identical gate issues.", "cyan"))
        print()

    print("=" * 70)
    verdict = "BEATS" if score_c > score_b else "TIES WITH" if score_c == score_b else "LOSES TO"
    print(style(f"  FINAL: Onklaud 5 {verdict} Fable 5", "bold"))
    print(f"  {score_c}/10 council vs {score_b}/10 single model | Delta: {delta:+d}")
    print("=" * 70)
    print()

    sys.exit(0 if score_c >= 8 else 1)


def cmd_benchmark(args):
    """Full benchmark: score single-model output, run council review, compare."""
    draft = args.draft
    if not draft and args.draft_file:
        draft = Path(args.draft_file).read_text(encoding="utf-8", errors="ignore")
    if not draft:
        draft = sys.stdin.read()
    if not draft.strip():
        print("Error: No draft text provided (--draft, --draft-file, or stdin)", file=sys.stderr)
        sys.exit(1)

    prompt = args.prompt or "Code/architecture task"
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8", errors="ignore")

    review_type = args.type

    print()
    print(style("  Onklaud 5 <=> Starting benchmark...", "cyan"))
    print(f"  Review type: {review_type} | Draft size: {len(draft)} chars")
    print()

    # Phase 1: Run council full mode
    print(style("  [1/2] Running Onklaud 5 council...", "cyan"))
    council_result = run_council_full(draft, prompt, review_type)

    if council_result.get("error"):
        print(style(f"  Council error: {council_result['error']}", "red"))
        sys.exit(1)

    print(f"  Council score: {council_result.get('final_score', '?')}/10")
    print()

    # Phase 2: Compare
    print(style("  [2/2] Comparing against single model baseline...", "cyan"))
    result = compare_outputs(draft, council_result, prompt, review_type)

    # Save result as JSON
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "prompt": prompt[:500],
                "type": review_type,
                "result": result,
                "council_trace": council_result.get("pipeline", "")
            }, f, indent=2, ensure_ascii=False)
        print(f"  Results saved to {args.output}")

    sys.exit(0 if result["council_passed"] else 1)


def cmd_list_benchmarks(args):
    """Print known benchmark scores from BENCHMARKS.md."""
    if BENCHMARKS_MD.exists():
        content = BENCHMARKS_MD.read_text(encoding="utf-8", errors="ignore")
        # Extract the table section
        in_table = False
        for line in content.split("\n"):
            if "| Benchmark" in line:
                in_table = True
            if in_table:
                print(line)
                if not line.strip() or (line.strip() and not line.startswith("|")):
                    in_table = False
                    break
    else:
        print("BENCHMARKS.md not found. Run with --help for usage.")


def main():
    # Force UTF-8 output on Windows
    if hasattr(sys.stdout, 'buffer'):
        try:
            sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Onklaud 5 Benchmark - Compare council output vs single-model",
        epilog="""
Examples:
  python onklaud-5/benchmark.py --prompt "Write a sort function" --draft "def sort(arr): return sorted(arr)" --type code
  python onklaud-5/benchmark.py --prompt-file task.txt --draft-file answer.txt --type architecture
  python onklaud-5/benchmark.py --baseline single_model.txt --council council_output.txt --type code
  python onklaud-5/benchmark.py --list
        """
    )
    sub = parser.add_subparsers(dest="mode")

    # benchmark mode (default)
    p_bench = sub.add_parser("bench", help="Full benchmark: score + council review")
    p_bench.add_argument("--prompt", help="Task description/prompt")
    p_bench.add_argument("--prompt-file", help="File containing the task prompt")
    p_bench.add_argument("--draft", help="Single-model output text to review")
    p_bench.add_argument("--draft-file", help="File containing single-model output")
    p_bench.add_argument("--type", choices=["code", "architecture"], default="code")
    p_bench.add_argument("--output", "-o", help="Save results to JSON file")

    # compare mode (direct head-to-head)
    p_cmp = sub.add_parser("compare", help="Direct comparison of two outputs")
    p_cmp.add_argument("--baseline", help="Single-model output text")
    p_cmp.add_argument("--baseline-file", help="File with single-model output")
    p_cmp.add_argument("--council", help="Council-enhanced output text")
    p_cmp.add_argument("--council-file", help="File with council output")
    p_cmp.add_argument("--type", choices=["code", "architecture"], default="code")

    # list mode
    p_list = sub.add_parser("list", help="Show known benchmark scores")

    args = parser.parse_args()

    if args.mode == "bench" or args.mode is None:
        # Default to bench mode if no subcommand
        cmd_benchmark(args)
    elif args.mode == "compare":
        cmd_compare(args)
    elif args.mode == "list":
        cmd_list_benchmarks(args)


if __name__ == "__main__":
    main()
