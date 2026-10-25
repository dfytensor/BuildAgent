# -*- coding: utf-8 -*-
"""DeepSeek L9-01 answerer 复现: 大预算 / thinking禁用 / 精简提示"""
import json
import os
import time
import requests

AUTH = json.load(open(os.path.expanduser("~/.local/share/opencode/auth.json"), encoding="utf-8"))
KEY = AUTH["deepseek"]["key"]
BASE = "https://api.deepseek.com/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
MODEL = "deepseek-flash"

tr = json.load(open(r"artifacts\trace\v11_metric2_SQL-L9-01.json", encoding="utf-8"))
user = tr["trace"][0]["user"]
steps = tr["trace"][0]["steps"]
content = f"用户问题: {user}"
for i, st in enumerate(steps):
    from_summ = json.dumps(st["result"], ensure_ascii=False)
    content += f"\n[工具{i+1}结果] {from_summ[:900]}"

SYS = ("你是数据分析回答器。只依据给定的查询结果回答用户问题。"
       "规则: 第一行输出FINAL; 答案必须包含具体数字或文本结果; 数字不要用万/亿; "
       "按题目要求保留小数; 结果里没有的信息不要编造; 若结果是错误信息(error)则回答查询失败+原因。")

def call(tag, msgs, mx=6000, extra=None):
    body = {"model": MODEL, "messages": msgs, "max_tokens": mx, "temperature": 0}
    if extra:
        body.update(extra)
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", headers=H, data=json.dumps(body), timeout=300)
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"[{tag}] {dt:.1f}s HTTP {r.status_code}: {r.text[:120]}")
        return
    d = r.json()
    ch = d["choices"][0]
    m = ch.get("message", {})
    u = d.get("usage", {})
    print(f"[{tag}] {dt:.1f}s finish={ch.get('finish_reason')} usage={u.get('completion_tokens')} "
          f"reasoning={u.get('completion_tokens_details', {}).get('reasoning_tokens')}")
    print(f"   content={repr((m.get('content') or ''))[:120]}")
    print(f"   reasoning={repr((m.get('reasoning_content') or ''))[:80]}")

base = [{"role": "system", "content": SYS}, {"role": "user", "content": content}]
call("orig-6000", base)
call("thinking-off", base, extra={"thinking": {"type": "disabled"}})
short = [{"role": "system", "content": "只依据结果输出一行FINAL+答案, 禁止分析过程。"},
         {"role": "user", "content": content[:1200]}]
call("short-6000", short)
