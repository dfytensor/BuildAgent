# -*- coding: utf-8 -*-
"""免费候选模型探测: 可用性/工具调用/中文"""
import os
import requests
import json
import time

KEY = "os.environ.get("OPENROUTER_API_KEY", "")"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
CANDS = ["nvidia/nemotron-3-super-120b-a12b:free",
         "google/gemma-4-31b-it:free",
         "openrouter/free",
         "dots-studio/dots-3-note-preview:free"]
TOOLS = [{"type": "function", "function": {"name": "sqlite_query",
          "description": "查询电商SQLite数据库(表: customers/products/orders/order_items)",
          "parameters": {"type": "object", "properties": {"sql": {"type": "string"}},
          "required": ["sql"]}}}]

for model in CANDS:
    print(f"== {model} ==")
    messages = [
        {"role": "system", "content": "你是数据分析规划器, 已连接电商数据库, 需要数据就调用sqlite_query。"},
        {"role": "user", "content": "数码类商品有多少件?"},
    ]
    body = {"model": model, "max_tokens": 400, "temperature": 0,
            "messages": messages, "tools": TOOLS}
    try:
        t0 = time.time()
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=H, data=json.dumps(body), timeout=180)
        dt = time.time() - t0
        if r.status_code != 200:
            print(f"  [{dt:.0f}s] HTTP {r.status_code}: {r.text[:100]}")
            continue
        m = r.json()["choices"][0]["message"]
        tcs = m.get("tool_calls")
        if tcs:
            print(f"  [{dt:.0f}s] tool_calls: {tcs[0]['function']['name']}, {tcs[0]['function']['arguments'][:90]}")
        else:
            print(f"  [{dt:.0f}s] no tool_calls, content: {repr((m.get('content') or ''))[:80]}")
    except Exception as e:
        print(f"  EXC {type(e).__name__}: {str(e)[:80]}")