"""10-gate quality scoring - offline, zero API calls. Called via: python onklaud-5/quality_gate.py '<json_output>'"""
import sys, json, re

class Gate:
    def __init__(self, name, severity, check_fn, domain="all"):
        self.name = name
        self.severity = severity
        self.check = check_fn
        self.domain = domain

GATE_REGISTRY = []

def gate(name, severity, domain="all"):
    def decorator(fn):
        GATE_REGISTRY.append(Gate(name, severity, fn, domain))
        return fn
    return decorator

class GateResult:
    def __init__(self, name, passed, issues):
        self.name = name
        self.passed = passed
        self.issues = issues
    def to_dict(self):
        return {"name": self.name, "passed": self.passed, "issues": self.issues}

# BLOCKER gates (3x weight)
@gate("ErrorHandling", "blocker", "coding")
def chk_error_handling(output, ctx):
    issues = []
    if "async" in output and "try" not in output and "catch" not in output and "except" not in output:
        issues.append("Async operations should have error handling (try/catch)")
    return GateResult("ErrorHandling", len(issues) == 0, issues)

@gate("TypeSafety", "blocker", "coding")
def chk_type_safety(output, ctx):
    issues = []
    if "any" in output.lower():
        issues.append("Contains 'any' type - prefer stricter types")
    return GateResult("TypeSafety", len(issues) <= 1, issues)

@gate("EdgeCases", "blocker", "coding")
def chk_edge_cases(output, ctx):
    issues = []
    indicators = ["null", "undefined", "empty", "invalid", "edge", "boundary"]
    found = sum(1 for ind in indicators if ind in output.lower())
    if found < 2:
        issues.append("Few edge case indicators - may miss null/empty/invalid inputs")
    return GateResult("EdgeCases", found >= 1, issues)

@gate("FailureModes", "blocker", "architecture")
def chk_failure_modes(output, ctx):
    issues = []
    fm_kw = ["failure", "failover", "retry", "circuit breaker", "dead letter", "dlq",
             "timeout", "degraded", "fallback", "redundancy", "graceful"]
    found = sum(1 for kw in fm_kw if kw in output.lower())
    if found < 2:
        issues.append("Architecture should address failure modes (retry, circuit breaker, graceful degradation)")
    return GateResult("FailureModes", found >= 2, issues)

@gate("ExcellenceThreshold", "blocker")
def chk_excellence_threshold(output, ctx):
    issues = []
    if len(output) < 100:
        issues.append(f"Output too short ({len(output)} chars) - insufficient depth")
    if output.count("\n") < 3:
        issues.append("Output lacks structure - use paragraphs/sections")
    return GateResult("ExcellenceThreshold", len(issues) == 0, issues)

# CRITICAL gates (2x weight)
@gate("DRY", "critical", "coding")
def chk_dry(output, ctx):
    issues = []
    lines = output.split("\n")
    # Only flag lines >= 40 chars that aren't pure punctuation/brackets
    significant = [l.strip() for l in lines
                   if len(l.strip()) > 40 and not re.match(r'^[{}()\[\];,.\s]+$', l.strip())]
    if len(significant) > 10:
        seen = {}
        for i, line in enumerate(significant):
            normalized = re.sub(r'\s+', '', line)
            if normalized in seen:
                issues.append(f"Potential duplication: line {seen[normalized]+1} and {i+1}")
                break
    return GateResult("DRY", len(issues) == 0, issues)

@gate("DeadCode", "critical", "coding")
def chk_dead_code(output, ctx):
    issues = []
    if "TODO" in output:
        issues.append("Contains TODO - either implement or remove")
    dead_patterns = ["console.log", "debugger", "print("]
    for pat in dead_patterns:
        if pat in output:
            issues.append(f"Contains debug statement: {pat}")
            break
    return GateResult("DeadCode", len(issues) == 0, issues)

@gate("ScalingStrategy", "critical", "architecture")
def chk_scaling(output, ctx):
    issues = []
    scale_kw = ["scale", "shard", "partition", "replica", "horizontal", "vertical",
                "throughput", "bottleneck", "load balanc"]
    found = sum(1 for kw in scale_kw if kw in output.lower())
    if found < 2:
        issues.append("Architecture should discuss scaling strategy")
    return GateResult("ScalingStrategy", found >= 2, issues)

@gate("Tradeoffs", "critical", "architecture")
def chk_tradeoffs(output, ctx):
    issues = []
    trade_kw = ["tradeoff", "trade-off", "cost", "latency vs", "consistency vs",
                "however", "downside", "limitation", "caveat"]
    found = sum(1 for kw in trade_kw if kw in output.lower())
    if found < 1:
        issues.append("Architecture should mention tradeoffs (every decision has a cost)")
    return GateResult("Tradeoffs", found >= 1, issues)

# WARNING gates (1x weight)
@gate("Clarity", "warning")
def chk_clarity(output, ctx):
    issues = []
    if "```" in output and output.count("```") % 2 != 0:
        issues.append("Unclosed code block")
    if "http://" in output:
        issues.append("Uses HTTP (prefer HTTPS)")
    return GateResult("Clarity", len(issues) == 0, issues)

SEVERITY_WEIGHT = {"blocker": 3, "critical": 2, "warning": 1}

def score_output(output, domain="general"):
    ctx = {"domain": domain}
    applicable = [g for g in GATE_REGISTRY if g.domain in (domain, "all")]
    results = []
    total_weight = 0
    weighted_sum = 0
    for gate in applicable:
        result = gate.check(output, ctx)
        results.append(result)
        w = SEVERITY_WEIGHT.get(gate.severity, 1)
        total_weight += w
        if result.passed:
            weighted_sum += w
    if total_weight == 0:
        return {"score": 10, "passed": True, "gates": [], "issues": []}
    raw_score = (weighted_sum / total_weight) * 10
    score = round(raw_score)
    passed = score >= 10
    all_issues = []
    for r in results:
        all_issues.extend(r.issues)
    return {"score": score, "passed": passed, "gates": [r.to_dict() for r in results], "issues": all_issues}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"score": 0, "passed": False, "error": "Usage: python quality_gate.py '<text_to_score>' [domain]"}))
        sys.exit(1)
    domain = sys.argv[2] if len(sys.argv) > 2 else "general"
    result = score_output(sys.argv[1], domain)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)
