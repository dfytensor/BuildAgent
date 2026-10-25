# -*- coding: utf-8 -*-
"""deepseek-flash 行为探针: QA / 原生tools / 重提示下的思考与正文"""
import json
import os
import time
import requests

AUTH = json.load(open(os.path.expanduser("~/.local/share/opencode/auth.json"), encoding="utf-8"))
KEY = AUTH["deepseek"]["key"]
BASE = "https://api.deepseek.com/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
MODEL = "deepseek-flash"

TOOLS = [{"type": "function", "function": {"name": "sqlite_query",
          "description": "查询电商SQLite数据库(表: customers/products/orders/order_items; 宽表v_sales含销售额amount)",
          "parameters": {"type": "object", "properties": {"sql": {"type": "string"}},
          "required": ["sql"]}}}]

def call(tag, messages, mx=600, tools=None):
    body = {"model": MODEL, "messages": messages, "max_tokens": mx, "temperature": 0}
    if tools:
        body["tools"] = tools
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", headers=H, data=json.dumps(body), timeout=180)
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"[{tag}] HTTP {r.status_code}: {r.text[:150]}")
        return
    d = r.json()
    ch = d["choices"][0]
    m = ch.get("message", {})
    print(f"[{tag}] {dt:.1f}s finish={ch.get('finish_reason')} usage={d.get('usage')}")
    print(f"   content={repr((m.get('content') or ''))[:120]}")
    print(f"   reasoning={repr((m.get('reasoning_content') or ''))[:100]}")

call("QA", [{"role": "user", "content": "1+1等于几? 只回答数字"}], 100)

call("TOOLS", [
    {"role": "system", "content": "你是数据分析规划器, 已连接电商数据库, 需要数据就调用sqlite_query。"},
    {"role": "user", "content": "数码类商品有多少件?"},
], 600, TOOLS)

rows = json.dumps({"columns": ["label", "value"],
                   "rows": [["家居", 6927639.05], ["家电", 72829932.03], ["数码", 63715349.92],
                            ["服饰", 14524720.96], ["美妆", 8819823.84], ["食品", 3523609.12]]},
                  ensure_ascii=False)
call("ANSWERER", [
    {"role": "system", "content": "你是数据分析回答器。只依据给定的查询结果回答用户问题。第一行输出FINAL; 答案必须包含具体数字。"},
    {"role": "user", "content": f"用户问题: 各类目销售额是多少?\n[工具1结果] {rows}"},
], 3000)
