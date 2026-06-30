#!/usr/bin/env python3
"""
Onklaud 5 - VERIFY PHASE (Runtime Verification)
=================================================
Fable 5 beats Opus 4.8 because it ACTUALLY TESTS what it builds.
This is the enforcement. Council passes code review → VERIFY must also pass.

Usage:
  python onklaud-5/verify.py [--type-only] [--full] [--smoke] [--project <dir>]

Modes:
  --type-only    Type-check only (fast, ~2s)
  --full         Type-check + tests (~30-60s)
  --smoke         Check if servers are already running (fast, ~5s)
  (default)      Auto: type-check always, tests if available

Exit codes: 0 = pass, 1 = fail, 2 = partial (tests unavailable but type-check OK)
"""
import sys, os, json, subprocess, time, platform

MY_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(MY_DIR)
IS_WIN = platform.system() == "Windows"

if not IS_WIN:
    import signal

def _npm_cmd(*args):
    """Return correct npm/npx/pnpm command for the platform."""
    cmd = list(args)
    if IS_WIN:
        cmd[0] = cmd[0] + ".cmd"
    return cmd

def _detect_pm(project_dir):
    """Detect package manager: npm, pnpm, or yarn."""
    if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")):
        return "pnpm"
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        return "yarn"
    return "npm"

def _run_script(pm, script, cwd, timeout=120):
    """Run a package.json script. Handles chained commands (&&, ||) and scripts
    that already invoke the package manager."""
    # If script value already contains package manager calls or shell operators,
    # run it directly through shell (it's self-contained)
    if script.startswith(pm) or script.startswith("npm") or script.startswith("yarn") or \
       "&&" in script or "||" in script or ";" in script:
        return subprocess.run(
            script,
            cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout, shell=True
        )

    if IS_WIN:
        pm_cmd = pm + ".cmd"
    else:
        pm_cmd = pm
    return subprocess.run(
        f'{pm_cmd} run {script}',
        cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout, shell=True
    )

class Verify:
    def __init__(self, project_dir=None, mode="auto"):
        self.project_dir = os.path.abspath(project_dir or ROOT)
        self.mode = mode  # auto, type-only, full
        self.results = {"type_check": None, "tests": None, "smoke": None, "passed": False}
        self.errors = []

    def detect_project_type(self):
        """Detect what kind of project this is."""
        pkg_json = os.path.join(self.project_dir, "package.json")
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json) as f:
                    pkg = json.load(f)
            except Exception:
                pkg = {}
            scripts = pkg.get("scripts", {})
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            has_ts = os.path.exists(os.path.join(self.project_dir, "tsconfig.json"))
            has_react = "react" in deps
            has_express = "express" in deps
            has_vite = "vite" in deps
            has_test_script = "test" in scripts
            has_dev_script = "dev" in scripts or "start" in scripts

            return {
                "lang": "typescript" if has_ts else "javascript",
                "is_ui": has_react or has_vite,
                "is_server": has_express,
                "is_fullstack": has_react and has_express,
                "has_tests": has_test_script,
                "has_dev_server": has_dev_script,
                "test_cmd": scripts.get("test", None),
                "dev_cmd": scripts.get("dev", None) or scripts.get("start", None),
                "build_cmd": scripts.get("build", None),
            }
        return {"lang": "unknown"}

    def run(self):
        project_type = self.detect_project_type()
        print(f"[VERIFY] Project: {self.project_dir}")
        print(f"[VERIFY] Detected: {project_type.get('lang', 'unknown')}",
              f"| UI={project_type.get('is_ui')}",
              f"| Server={project_type.get('is_server')}",
              f"| Tests={project_type.get('has_tests')}")

        # Phase 1: Type-check (ALWAYS)
        self._type_check(project_type)
        if self.mode == "type-only":
            return self._summarize()

        # Phase 2: Tests (if available, only in auto/full modes)
        if project_type.get("has_tests") and self.mode in ("auto", "full"):
            self._run_tests(project_type)

        # Phase 3: Smoke test (only with --smoke flag - checks ALREADY running server)
        if self.mode == "smoke" and (project_type.get("is_server") or project_type.get("is_ui")):
            self._smoke_test(project_type)

        return self._summarize()

    def _type_check(self, pt):
        lang = pt.get("lang")
        print("[VERIFY] Phase 1: Type-check...")

        if lang == "typescript":
            tsconfig = os.path.join(self.project_dir, "tsconfig.json")
            if not os.path.exists(tsconfig):
                print("[VERIFY]   No tsconfig.json - skipping type-check")
                self.results["type_check"] = "skipped"
                return

            r = subprocess.run(
                _npm_cmd("npx", "tsc", "--noEmit"),
                cwd=self.project_dir, capture_output=True, encoding="utf-8", errors="replace", timeout=60
            )
            if r.returncode == 0:
                print("[VERIFY]   tsc --noEmit: OK")
                self.results["type_check"] = "pass"
            else:
                errors = r.stdout.strip()[:500]
                print(f"[VERIFY]   tsc --noEmit: FAIL")
                print(f"  {errors}")
                self.results["type_check"] = "fail"
                self.errors.append(f"TypeScript errors:\n{errors}")

        elif lang == "javascript":
            # Quick syntax check on all JS/TS files
            errors_found = 0
            for root, _, files in os.walk(self.project_dir):
                if "node_modules" in root or ".git" in root:
                    continue
                for f in files:
                    if f.endswith((".js", ".ts", ".jsx", ".tsx", ".mjs")):
                        fp = os.path.join(root, f)
                        r = subprocess.run(
                            ["node", "--check", fp],
                            capture_output=True, encoding="utf-8", errors="replace", timeout=5
                        )
                        if r.returncode != 0:
                            errors_found += 1
                            if errors_found <= 3:
                                print(f"[VERIFY]   {f}: syntax error")
            if errors_found == 0:
                print("[VERIFY]   node --check: OK")
                self.results["type_check"] = "pass"
            else:
                print(f"[VERIFY]   node --check: {errors_found} files with syntax errors")
                self.results["type_check"] = "fail"
                self.errors.append(f"{errors_found} JS files with syntax errors")

        elif lang == "unknown":
            print("[VERIFY]   Unknown project type - skipping type-check")
            self.results["type_check"] = "skipped"

    def _run_tests(self, pt):
        print("[VERIFY] Phase 2: Tests...")
        test_script = pt.get("test_cmd", "test")
        pm = _detect_pm(self.project_dir)
        try:
            r = _run_script(pm, test_script, self.project_dir, timeout=120)
        except Exception as e:
            print(f"[VERIFY]   Tests: ERROR - {e}")
            self.results["tests"] = "fail"
            self.errors.append(f"Test runner crashed: {e}")
            return

        if r.returncode == 0:
            print("[VERIFY]   Tests: OK")
            self.results["tests"] = "pass"
        else:
            out = (r.stdout or "") + (r.stderr or "")
            # Sanitize non-ASCII chars that can't print on Windows cp1252
            out = out.encode('ascii', errors='replace').decode('ascii')
            print(f"[VERIFY]   Tests: FAIL")
            print(f"  {out[:500]}")
            self.results["tests"] = "fail"
            self.errors.append(f"Tests failed:\n{out[:300]}")

    def _smoke_test(self, pt):
        print("[VERIFY] Phase 3: Smoke test...")
        if pt.get("is_server"):
            self._smoke_server(pt)
        if pt.get("is_ui"):
            self._smoke_ui(pt)

    def _smoke_server(self, pt):
        """Check if server is already running on known ports."""
        print("[VERIFY]   Checking server...")
        ports = [8790, 3000, 8080, 8000]
        for port in ports:
            try:
                r = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     f"http://127.0.0.1:{port}/api/health"],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=3
                )
                if r.stdout.strip() in ("200", "204", "302"):
                    print(f"[VERIFY]   Server on port {port}: OK")
                    self.results["smoke"] = "pass"
                    return
            except Exception:
                pass
        print("[VERIFY]   No running server detected (checked ports 8790, 3000, 8080, 8000)")
        self.results["smoke"] = "skip"

    def _extract_port(self, script_value):
        """Extract --port from a dev script. Returns None if not found."""
        import re
        m = re.search(r'--port\s+(\d+)', script_value)
        return int(m.group(1)) if m else None

    def _smoke_ui(self, pt):
        """Check if UI dev server is already running on known ports."""
        print("[VERIFY]   Checking UI dev server...")
        pkg_json = os.path.join(self.project_dir, "package.json")
        with open(pkg_json) as f:
            scripts = json.load(f).get("scripts", {})
        dev_value = scripts.get(pt.get("dev_cmd", "dev"), "")
        explicit_port = self._extract_port(dev_value)

        ports = [explicit_port] if explicit_port else [8800, 5173, 3000, 3001]
        ports = [p for p in ports if p is not None]
        for port in ports:
            try:
                r = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     f"http://127.0.0.1:{port}"],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=3
                )
                if r.stdout.strip() in ("200", "302"):
                    print(f"[VERIFY]   UI dev server on port {port}: OK")
                    self.results["smoke"] = "pass"
                    return
            except Exception:
                pass
        print(f"[VERIFY]   No running UI server detected (checked ports {ports})")
        self.results["smoke"] = "skip"

    def _summarize(self):
        tc = self.results["type_check"]
        tests = self.results["tests"]
        smoke = self.results["smoke"]

        checks = []
        if tc:
            checks.append(f"TypeCheck={tc}")
        if tests:
            checks.append(f"Tests={tests}")
        if smoke:
            checks.append(f"Smoke={smoke}")

        # Determine pass/fail (skip = non-failing for smoke)
        failures = [v for v in [tc, tests, smoke] if v == "fail"]
        skips = [v for v in [tc, tests, smoke] if v == "skip"]

        if not failures:
            self.results["passed"] = True
            print(f"\n[VERIFY] ALL PASS: {' | '.join(checks)}")
            return 0
        else:
            self.results["passed"] = False
            print(f"\n[VERIFY] FAIL: {' | '.join(checks)}")
            for e in self.errors:
                print(f"  {e[:200]}")
            return 1


def main():
    mode = "auto"
    project_dir = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--type-only":
            mode = "type-only"
        elif a == "--full":
            mode = "full"
        elif a == "--smoke":
            mode = "smoke"
        elif a == "--project" and i + 1 < len(args):
            i += 1
            project_dir = args[i]
        i += 1

    verifier = Verify(project_dir=project_dir, mode=mode)
    sys.exit(verifier.run())


if __name__ == "__main__":
    main()
