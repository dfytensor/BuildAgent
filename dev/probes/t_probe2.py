# -*- coding: utf-8 -*-
"""账户配额状态 + 免费候选横扫(每模型1次工具调用探针)"""
import os
import requests
import json
import time

KEY = "os.environ.get("OPENROUTER_API_KEY", "")"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
URL = "https://openrouter.ai/api/v1/chat/completions"

print("== 账户状态 ==")
try:
    r = requests.get("https://openrouter.ai/api/v1/auth/key", headers=H, timeout=30)
    print(json.dumps(r.json(), ensure_ascii=False)[:400])
except Exception as e:
    print("FAIL", type(e).__name__)

CANDS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "dots-studio/dots-3-note-preview:free",
    "poolside/laguna-s-2.1:free",
]
TOOLS = [{"type": "function", "function": {"name": "sqlite_query",
          "description": "查询电商SQLite数据库(表: customers/products/orders/order_items)",
          "parameters": {"type": "object", "properties": {"sql": {"type": "string"}},
          "required": ["sql"]}}}]

print("\n== 候选探针(工具调用) ==")
for model in CANDS:
    msgs = [
        {"role": "system", "content": "你是数据分析规划器, 已连接电商数据库, 需要数据就调用sqlite_query。"},
        {"role": "user", "content": "数码类商品有多少件?"},
    ]
    body = {"model": model, "max_tokens": 300, "temperature": 0,
            "messages": msgs, "tools": TOOLS}
    try:
        t0 = time.time()
        r = requests.post(URL, headers=H, data=json.dumps(body), timeout=180)
        dt = time.time() - t0
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            tcs = m.get("tool_calls")
            if tcs:
                print(f"[{dt:.0f}s] OK  tool: {tcs[0]['function']['name']} {tcs[0]['function']['arguments'][:70]}")
            else:
                print(f"[{dt:.0f}s] OK  no-tool-call content={repr((m.get('content') or ''))[:60]}")
        else:
            raw = ""
            try:
                raw = r.json()["error"].get("metadata", {}).get("raw", "") or r.json()["error"].get("message", "")
            except Exception:
                raw = r.text[:100]
            kind = "日配额耗尽" if "free-models-per-day" in raw else ("上游拥塞" if "temporarily" in raw else "其他")
            print(f"[{dt:.0f}s] {r.status_code} [{kind}] {raw[:90]}")
    except Exception as e:
        print(f"EXC {type(e).__name__}: {str(e)[:70]}")
    time.sleep(2)