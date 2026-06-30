# Onklaud 5 v3.2 - 🎠⚡🔮🗜️ Design Spec

**Date:** 2026-06-22
**Goal:** Exceed Fable 5 with 🎠 Ponytail Native + 🔮 GLM +50% + 🗜️ Headroom
**Philosophy:** Ponytail filters 85% before API. GLM at 3 touchpoints. Headroom compresses 60-95%.

## Architecture v3.2

```
REQUÊTE UTILISATEUR
      │
      ▼
🎠 PONYTAIL LADDER (step 0 - 0 tokens)
  stdlib → native → existing dep → shortest
  85% resolved here. x10 speed.
      │
      ▼ (seulement si ladder vide)
🔮 GLM PRE-DESIGN (touchpoint 1 - 16000 tokens)
  Architecture sketch before Kimi codes
      │
      ▼
⚡ KIMI K2.7 CODE - generation (64000 tokens)
      │
      ▼
⚡+🔮 DUAL REVIEW (touchpoint 2 - Kimi+GLM both review)
  Scores averaged. Different blind spots.
      │
      ▼
🔮 GLM ARBITRATION (touchpoint 3 - final synthesis)
      │
      ▼
GATE 10/10 → 🔨 VERIFY → 🗜️ HEADROOM (60-95% compression)
```

## Components

| Component | Rôle | Tokens | Cost |
|-----------|------|--------|------|
| 🎠 ponytail_ladder.py | stdlib→native→dep→shortest | 0 | $0 |
| 🔮 GLM 5.2 | pre-design + dual review + arbitration (+50%) | 64000 | $1.40/$4.40/M |
| ⚡ Kimi K2.7 | code generation + code review | 64000 | $0.95/$4.00/M |
| 🔮 pre_check.py | immune memory scan before write | 0 | $0 |
| 🚦 quality_gate.py | 10-gate scoring | 0 | $0 |
| 🔨 verify.py | type-check + tests | 0 | $0 |
| 🗜️ Headroom | 60-95% context compression | 0 | $0 |

## GLM +50% Breakdown

| Touchpoint | Phase | Model | Max Tokens |
|-----------|-------|-------|------------|
| 1 | Pre-design | GLM 5.2 | 16000 |
| 2 | Dual review | GLM 5.2 | 64000 |
| 3 | Arbitration | GLM 5.2 | 64000 |

## Anti-Saturation Strategy

1. CLAUDE.md: 16+25 lines (75% reduction)
2. Session-start hook: 3 lines (85% reduction)
3. Post-write hook: silent on success
4. Headroom: 60-95% compression at shell level
5. 3 phrases max per response

## Files

| File | Status |
|------|--------|
| `council.py` | v3.2 - GLM pre-design, dual review, reasoning effort |
| `ponytail_ladder.py` | 50+ stdlib patterns, 15+ native, word-level matching |
| `pre_check.py` | Immune memory pre-scan, 8 failure categories |
| `test_pipeline.py` | 25 tests, end-to-end |
| `nadirclaw/config.yaml` | v3.2 - 7 pipeline steps |
| `~/.claude/headroom-claude.ps1` | PowerShell wrapper |

## Immutable Rules

1. 🎠 Ponytail Ladder FIRST - always, before any code
2. 🔮 GLM +50% - pre-design + dual review + arbitration
3. Pipeline trace OBLIGATOIRE: `[🎠→⚡K(X/10)→🔮G→gate(X/10)]`
4. Gate 10/10 non-negotiable
5. DeepSeek = emergency fallback only
6. Token cost NOT a constraint
7. 3 phrases max (anti-saturation)
8. Headroom recommended: `. ~/.claude/headroom-claude.ps1`
