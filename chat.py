#!/usr/bin/env python3
"""Onklaud 5 - Colored Terminal Chat
Zero dependencies. Pure ANSI. Each model has its own color identity.
Usage: python onklaud-5/chat.py
"""

import sys, json, os, re, io
import urllib.request, urllib.error
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── ANSI Colors ────────────────────────────────────────────────────
R = "\033[0m"; B = "\033[1m"; D = "\033[2m"

# DeepSeek - Ocean Blue
DS  = {"fg":"\033[38;2;74;144;217m","bd":"\033[38;2;74;144;217m",
       "lb":"\033[38;2;255;255;255;48;2;74;144;217m","di":"\033[38;2;100;160;220m"}

# Kimi - Matrix Green
KIM = {"fg":"\033[38;2;0;255;65m","bd":"\033[38;2;0;255;65m",
       "lb":"\033[38;2;0;20;0;48;2;0;255;65m","di":"\033[38;2;50;200;80m"}

# GLM - Royal Purple
GLM = {"fg":"\033[38;2;179;71;234m","bd":"\033[38;2;179;71;234m",
       "lb":"\033[38;2;255;255;255;48;2;179;71;234m","di":"\033[38;2;150;100;200m"}

SYS = "\033[38;2;255;180;50m"; ERR = "\033[38;2;255;60;60m"
OK = "\033[38;2;50;255;100m"; MUT = "\033[38;2;100;100;100m"

MODELS = {
    "deepseek": {"name":"DeepSeek V4 Pro","emoji":"🌊","role":"PRIMARY","c":DS,
                 "api":"deepseek","model_id":"deepseek-chat"},
    "kimi":     {"name":"Kimi K2.7 Code","emoji":"⚡","role":"CODING","c":KIM,
                 "api":"openrouter","model_id":"moonshotai/kimi-k2.7-code"},
    "glm":      {"name":"GLM 5.2","emoji":"🔮","role":"ARBITRATOR","c":GLM,
                 "api":"openrouter","model_id":"z-ai/glm-5.2"},
}

def load_keys():
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists(): env = Path(".env")
    keys = {}
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys

def call_api(model_id, prompt, api_key, provider="openrouter"):
    """Call OpenRouter or DeepSeek API."""
    if provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}

    data = json.dumps({
        "model": model_id,
        "messages": [{"role":"user","content":prompt}],
        "max_tokens": 600,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(url, data=data, headers={**headers, "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
            msg = body.get("choices",[{}])[0].get("message",{})
            content = msg.get("content")
            if not content:
                reasoning = msg.get("reasoning","")
                if reasoning:
                    return f"[GLM reasoning - increase max_tokens]\n{reasoning[:300]}..."
                return f"[empty response] {json.dumps(body)[:200]}"
            return content
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return f"Error: {e}"

def strip_ansi(text):
    return re.sub(r'\033\[[^m]*m', '', text)

def render(model_key, text, width=72):
    m = MODELS[model_key]; c = m["c"]
    label = f" {m['emoji']} {m['name']}  ·  {m['role']} "
    out = [
        f"\n{c['bd']}╭{'─'*(width-2)}╮{R}",
        f"{c['lb']}{label}{R}{c['bd']}{' '*(width-2-len(strip_ansi(label)))}{R}",
        f"{c['bd']}│{R}{' '*(width-2)}{c['bd']}│{R}"
    ]
    for para in text.split("\n"):
        if not para.strip():
            out.append(f"{c['bd']}│{R}")
            continue
        words = para.split(" "); line = ""
        for w in words:
            test = line + (" " if line else "") + w
            if len(test) <= width - 4:
                line = test
            else:
                pad = width - 2 - len(line)
                out.append(f"{c['bd']}│{R} {c['fg']}{line}{R}{' '*max(0,pad)}{c['bd']}│{R}")
                line = w
        if line:
            pad = width - 2 - len(line)
            out.append(f"{c['bd']}│{R} {c['fg']}{line}{R}{' '*max(0,pad)}{c['bd']}│{R}")
    out.append(f"{c['bd']}╰{'─'*(width-2)}╯{R}")
    return "\n".join(out)

def classify(prompt):
    kw = ["code","function","class","bug","fix","implement","refactor",
          "test","compile","syntax","api","endpoint","query","sql","algorithm",
          "optimize","python","js","ts","react","component","hook","import","export","type"]
    return "kimi" if sum(1 for k in kw if k in prompt.lower()) >= 2 else "deepseek"

def splash():
    W = 64
    print(f"\n{SYS}{B}  {'='*W}{R}")
    print(f"{SYS}{B}  ||{R}  {DS['fg']}DEEPSEEK V4 PRO{R} {MUT}-> PRIMARY     70% of requests{R}  {SYS}{B}||{R}")
    print(f"{SYS}{B}  ||{R}  {KIM['fg']}KIMI K2.7 CODE{R}  {MUT}-> CODING      20% verification{R}  {SYS}{B}||{R}")
    print(f"{SYS}{B}  ||{R}  {GLM['fg']}GLM 5.2{R}         {MUT}-> ARBITRATOR  10% last resort{R}  {SYS}{B}||{R}")
    print(f"{SYS}{B}  {'='*W}{R}")
    print(f"\n{OK}{B}  ONKLAUD 5 - Beat Fable 5{R}  {MUT}~$5-8/month  |  Zero Custom Code{R}")
    print(f"{MUT}  /model deepseek|kimi|glm  |  /quit  |  or just type to chat (auto-routing){R}\n")

def main():
    keys = load_keys()
    ok = keys.get("OPENROUTER_API_KEY","")
    ds = keys.get("DEEPSEEK_API_KEY","")

    if not ok:
        print(f"{ERR}OPENROUTER_API_KEY not found. Set it in .env{R}")
        sys.exit(1)

    splash()
    current = "deepseek"

    while True:
        try:
            c = MODELS[current]["c"]
            prompt = input(f"{c['fg']}{B}onklaud>{R} ")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{MUT}Onklaud 5 shut down.{R}")
            break

        if not prompt.strip(): continue
        if prompt == "/quit":
            print(f"{MUT}Onklaud 5 shut down.{R}"); break
        if prompt.startswith("/model "):
            t = prompt.split()[1].lower()
            if t in MODELS:
                current = t
                print(f"{OK}→ {MODELS[t]['name']}{R}")
            else:
                print(f"{ERR}Unknown: {t}. Use deepseek, kimi, glm{R}")
            continue

        routed = classify(prompt) if current == "deepseek" else current
        mi = MODELS[routed]
        print(f"{mi['c']['di']}{B}→ {mi['name']} ({mi['role']}){R}")

        if mi["api"] == "openrouter":
            resp = call_api(mi["model_id"], prompt, ok, "openrouter")
        elif mi["api"] == "deepseek":
            if not ds:
                print(f"{ERR}DEEPSEEK_API_KEY not set. Use /model kimi or /model glm{R}")
                continue
            resp = call_api(mi["model_id"], prompt, ds, "deepseek")
        else:
            resp = "Unknown provider"

        print(render(routed, resp))

if __name__ == "__main__":
    main()
