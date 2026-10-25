# -*- coding: utf-8 -*-
"""8080 本地部署探测: 模型ID/连通性/原生工具调用/延迟"""
import requests
import json
import time

BASE = "http://127.0.0.1:8080/v1"

print("== 1. /v1/models ==")
try:
    r = requests.get(f"{BASE}/models", timeout=10)
    print(f"HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    print("FAIL", type(e).__name__, str(e)[:80])

print("\n== 2. 基础QA ==")
try:
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", timeout=120,
        headers={"Content-Type": "application/json"},
        data=json.dumps({"messages": [{"role": "user", "content": "1+1等于几? 只回答数字"}], "max_tokens": 512}))
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"[{dt:.1f}s] HTTP {r.status_code}: {r.text[:200]}")
    else:
        d = r.json()
        m = d.get("choices", [{}])[0].get("message", {})
        print(f"[{dt:.1f}s] model={d.get('model')!r} content={repr((m.get('content') or ''))[:80]}")
        print(f"      reasoning={repr((m.get('reasoning_content') or ''))[:80]}")
        print(f"      usage={d.get('usage')}")
except Exception as e:
    print(f"EXC {type(e).__name__}: {str(e)[:100]}")

print("\n== 3. 原生tools ==")
TOOLS = [{"type": "function", "function": {"name": "sqlite_query",
          "description": "查询电商SQLite数据库(表: customers/products/orders/order_items)",
          "parameters": {"type": "object", "properties": {"sql": {"type": "string"}},
          "required": ["sql"]}}}]
try:
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", timeout=120,
        headers={"Content-Type": "application/json"},
        data=json.dumps({"model": "gpt",
                         "max_tokens": 600, "temperature": 0,
                         "messages": [{"role": "system", "content": "你是数据分析规划器, 已连接电商数据库, 需要数据就调用sqlite_query。"},
                                      {"role": "user", "content": "数码类商品有多少件?"}],
                         "tools": TOOLS}))
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"[{dt:.1f}s] HTTP {r.status_code}: {r.text[:200]}")
    else:
        d = r.json()
        m = d.get("choices", [{}])[0].get("message", {})
        tcs = m.get("tool_calls")
        print(f"[{dt:.1f}s] model={d.get('model')!r}")
        if tcs:
            print(f"      tool_calls: {tcs[0]['function']['name']} {tcs[0]['function']['arguments'][:90]}")
        else:
            print(f"      no tool_calls: {repr((m.get('content') or ''))[:100]}")
        print(f"      reasoning={repr((m.get('reasoning_content') or ''))[:80]}")
        print(f"      usage={d.get('usage')}")
except Exception as e:
    print(f"EXC {type(e).__name__}: {str(e)[:100]}")
