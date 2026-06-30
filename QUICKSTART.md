# Onklaud 5 - Quick Start Guide

Get Onklaud 5 running in 5 minutes.

## Step 1: Get an OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up (free, no credit card required for trial credits)
3. Go to https://openrouter.ai/keys
4. Create a new key
5. Copy it (starts with `sk-or-v1-`)

## Step 2: Install

```bash
git clone https://github.com/KorroAi/onklaud-5.git
cd onklaud-5
```

Python 3.10+ required. Optional deps for PDF reports:
```bash
pip install fpdf2 pyyaml
```

## Step 3: Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your key:
```
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
```

## Step 4: Verify

```bash
# Check connectivity (no API cost)
python test_pipeline.py
# Expected: 24/25 passed, 0 failed

# Check council status
python council.py status
# Expected: "Council status: OPERATIONAL"
```

## Step 5: First Council Run

```bash
# Review a code file
python council.py loop --type code \
  --prompt "Review this for bugs and edge cases" \
  --draft-file path/to/your/code.py
```

## Step 6: Try Ponytail (0 cost)

```bash
# These are FREE - no API calls
python ponytail_ladder.py --task "read a JSON config file" --json
python ponytail_ladder.py --task "generate a random UUID" --json
python ponytail_ladder.py --task "dark mode toggle" --json
python ponytail_ladder.py --task "make a sticky header" --json
```

## Step 7: Immune Pre-Check

```bash
# Before coding, check against past failures
python pre_check.py --task "write an HTTP retry function" --json
python pre_check.py --task "parse JSON and cast to type" --json
```

## Optional: Local Model (DeepSeek, Ollama, etc.)

Add to `.env`:
```bash
LOCAL_MODEL_API_KEY=not-needed-for-ollama
LOCAL_MODEL_BASE_URL=http://localhost:11434/v1
LOCAL_MODEL_NAME=deepseek-chat
```

Or with LM Studio:
```bash
LOCAL_MODEL_BASE_URL=http://localhost:1234/v1
LOCAL_MODEL_NAME=local-model
```

## Cost Overview

| Task | API Calls | Cost |
|------|-----------|------|
| Ponytail check | 0 | $0 |
| Pre-check | 0 | $0 |
| Syntax gate | 0 | $0 |
| Quality gate | 0 | $0 |
| Verify | 0 | $0 |
| Dual review (code) | 2 calls (Kimi + GLM) | ~$0.005 |
| Full council loop | 3-5 calls | ~$0.01-0.02 |

57% of all tasks are resolved by Ponytail at $0.

## Troubleshooting

**"OPENROUTER_API_KEY not set"**
- Did you copy .env.example to .env?
- Check the key starts with `sk-or-v1-`

**"OpenRouter unreachable"**
- Check your internet connection
- Verify your key at https://openrouter.ai/keys
- Free tier has rate limits; wait a minute and retry

**"No draft provided"**
- Use `--draft-file path/to/file` or pipe via stdin
- Or write to a temp file and pass the path

**Windows encoding errors**
- All scripts use UTF-8. If you see encoding errors, run:
  `chcp 65001` in your terminal before running Python
