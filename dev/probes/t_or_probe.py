# -*- coding: utf-8 -*-
"""OpenRouter 当前状态: 连通/限流探测 x5"""
import os
import requests
import time
import json

KEY = "os.environ.get("OPENROUTER_API_KEY", "")"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
ok = 0
for i in range(5):
    t0 = time.time()
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=H,
                      data=json.dumps({"model": "minimax/minimax-m3.1-flash:free", "max_tokens": 30,
                                       "messages": [{"role": "user", "content": f"hi {i}"}]}), timeout=120)
    dt = time.time() - t0
    if r.status_code == 200:
        ok += 1
        print(f"{i}: {r.status_code} {dt:.1f}s {repr(r.json()['choices'][0]['message']['content'][:30])}")
    else:
        print(f"{i}: {r.status_code} {dt:.1f}s {r.text[:100]}")
    time.sleep(3.2)
print(f"成功 {ok}/5")