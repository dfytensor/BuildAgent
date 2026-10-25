# -*- coding: utf-8 -*-
"""xingchen-4B 探测: 对话/原生tools/延迟/推理行为"""
import os
import requests
import json
import time

KEY = "os.environ.get("OPENROUTER_API_KEY", "")"
URL = "https://openrouter.ai/api/v1/chat/completions"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
MODEL = "xingchen-agi/xing4.0-29b-a4b:free"


def chat(messages, mx=400, tools=None):
    body = {"model": MODEL, "messages": messages, "max_tokens": mx, "temperature": 0}
    if tools:
        body["tools"] = tools
    t0 = time.time()
    r = requests.post(URL, headers=H, data=json.dumps(body), timeout=300)
    dt = time.time() - t0
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:150]}", dt
    return r.json()["choices"][0]["message"], None, dt


print("== 1. 基础QA ==")
m, err, dt = chat([{"role": "user", "content": "1+1等于几? 只回答数字"}])
print(f"[{dt:.1f}s] err={err} -> {repr((m or {}).get('content', ''))[:80]}")
print("   reasoning_details:", bool((m or {}).get("reasoning_details")))

print("\n== 2. 业务问题(无schema) ==")
m, err, dt = chat([{"role": "user", "content": "数码类商品有多少件?"}])
print(f"[{dt:.1f}s] -> {repr((m or {}).get('content', ''))[:100]}")

print("\n== 3. 原生tools ==")
TOOLS = [{"type": "function", "function": {"name": "sqlite_query", "description": "查询电商SQLite数据库(表: customers/products/orders/order_items)",
          "parameters": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}}}]
m, err, dt = chat([{"role": "system", "content": "你是数据分析规划器, 已连接电商数据库, 需要数据就调用sqlite_query。"},
                   {"role": "user", "content": "数码类商品有多少件?"}], tools=TOOLS)
print(f"[{dt:.1f}s] err={err}")
if m:
    tcs = m.get("tool_calls")
    print("   tool_calls:", (tcs[0]["function"]["name"], tcs[0]["function"]["arguments"][:120]) if tcs else None)
    print("   content:", repr((m.get('content') or ''))[:80])