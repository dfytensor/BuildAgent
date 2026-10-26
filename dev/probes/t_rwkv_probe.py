# -*- coding: utf-8 -*-
"""8081 RWKV-7 探针: QA / 原生tools / 模板行为"""
import json
import time

import requests

BASE = "http://127.0.0.1:8081/v1"
H = {"Content-Type": "application/json"}
MODEL = "rwkv7-g1k-13.3b"

TOOLS = [{"type": "function", "function": {
    "name": "run_query",
    "description": "Run a read-only SQL query over the shop database",
    "parameters": {"type": "object",
                   "properties": {"sql": {"type": "string"}},
                   "required": ["sql"]}}}]


def chat(msgs, mx=300, tools=None):
    body = {"model": MODEL, "messages": msgs, "max_tokens": mx, "temperature": 0}
    if tools:
        body["tools"] = tools
    t0 = time.time()
    r = requests.post(BASE + "/chat/completions", headers=H, data=json.dumps(body), timeout=120)
    dt = time.time() - t0
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:150]}"
    d = r.json()
    ch = d["choices"][0]
    m = ch.get("message", {})
    tcs = m.get("tool_calls")
    out = (f"{dt:.1f}s finish={ch.get('finish_reason')} "
           f"content={repr((m.get('content') or ''))[:110]}")
    if tcs:
        fn = tcs[0]["function"]
        out += f" | TOOL {fn['name']}({str(fn.get('arguments'))[:90]})"
    return out


print("QA:", chat([{"role": "user", "content": "1+1等于几? 只回答数字"}], 100))
print("QA2:", chat([{"role": "user", "content": "中国的首都是哪里?"}], 100))
print("TOOLS:", chat([
    {"role": "system", "content": "你有run_query工具, 需要数据就调用它"},
    {"role": "user", "content": "商品表里有多少行? 用工具查"}], 600, TOOLS))
print("SYSTEM-ROLE:", chat([{"role": "system", "content": "你是数据分析助手"},
                            {"role": "user", "content": "简介一下你能做什么"}], 200))
