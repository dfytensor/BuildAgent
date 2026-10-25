# -*- coding: utf-8 -*-
"""xingchen-4B 耐心探针: 429风暴中找窗口"""
import os
import requests
import json
import time

KEY = "os.environ.get("OPENROUTER_API_KEY", "")"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
MODEL = "xingchen-agi/xing4.0-29b-a4b:free"
ok = 0
for i in range(8):
    try:
        t0 = time.time()
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=H,
                          data=json.dumps({"model": MODEL, "max_tokens": 60, "temperature": 0,
                                           "messages": [{"role": "user", "content": "1+1等于几? 只回答数字"}]}), timeout=120)
        dt = time.time() - t0
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            ok += 1
            print(f"{i}: {dt:.1f}s OK -> {repr((m.get('content') or '')[:50])}")
        else:
            print(f"{i}: {dt:.1f}s {r.status_code} {r.text[:80]}")
    except Exception as e:
        print(f"{i}: EXC {type(e).__name__}")
    time.sleep(30)
print(f"窗口成功率: {ok}/8")