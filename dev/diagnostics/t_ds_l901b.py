# -*- coding: utf-8 -*-
"""L9-01 精确复现: agent._answer_msgs 原样 vs 去chart vs 旧SYS"""
import json
import os
import sys
import time

sys.path.insert(0, "agent")
import requests
from v11_present import AgentV11
from v4_sandbox import ANSWER_SYS

AUTH = json.load(open(os.path.expanduser("~/.local/share/opencode/auth.json"), encoding="utf-8"))
KEY = AUTH["deepseek"]["key"]
BASE = "https://api.deepseek.com/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

tr = json.load(open(r"artifacts\trace\v11_metric2_SQL-L9-01.json", encoding="utf-8"))
t = tr["trace"][0]
user = t["user"]
steps = t["steps"]
obs = [(s.get("args", {}), s.get("result", {})) for s in steps]

ag = AgentV11()
def call(tag, msgs, mx=6000):
    body = {"model": "deepseek-flash", "messages": msgs, "max_tokens": mx, "temperature": 0}
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", headers=H, data=json.dumps(body), timeout=300)
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"[{tag}] HTTP {r.status_code}: {r.text[:120]}")
        return
    d = r.json()
    ch = d["choices"][0]
    m = ch.get("message", {})
    u = d.get("usage", {})
    print(f"[{tag}] {dt:.1f}s finish={ch.get('finish_reason')} usage={u.get('completion_tokens')} "
          f"reasoning={u.get('completion_tokens_details', {}).get('reasoning_tokens')}")
    print(f"   content={repr((m.get('content') or ''))[:110]}")
    print(f"   reasoning={repr((m.get('reasoning_content') or ''))[:90]}")

print("prompt chars:", sum(len(str(m['content'])) for m in ag._answer_msgs(user, obs)))
call("exact-agent-prompt", ag._answer_msgs(user, obs))
call("only-metric-step", ag._answer_msgs(user, obs[:1]))
old_sys = ANSWER_SYS.split("若结果是多行列表")[0]
msgs = ag._answer_msgs(user, obs)
msgs[0]["content"] = old_sys
call("old-SYS", msgs)
