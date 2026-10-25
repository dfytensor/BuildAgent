# -*- coding: utf-8 -*-
"""双查: 1) T4/T5案例轮级判分结构 2) L9-02 answerer 精确复现"""
import json
import requests
import time

# --- 1. T4-08 / T5-01 案例定义 ---
cases = json.load(open(r"eval\cases.json", encoding="utf-8"))
tmap = {c["id"]: c for s, lst in cases.items() for c in lst}
for cid in ("TOOL-T4-08", "TOOL-T5-01", "TOOL-T4-01"):
    c = tmap.get(cid)
    if not c:
        continue
    print(f"== {cid} ==")
    print(json.dumps(c, ensure_ascii=False)[:700])
    print()

# --- 2. L9-02 answerer 复现 ---
trace = json.load(open(r"artifacts\trace\v9_scaffold_SQL-L9-02.json", encoding="utf-8"))
user = trace["trace"][0]["user"]
steps = trace["trace"][0]["steps"]
content = f"用户问题: {user_text}" if False else f"用户问题: {user}"
for i, st in enumerate(steps):
    content += f"\n[工具{i+1}结果] {json.dumps(st['result'], ensure_ascii=False)[:900]}"
print(f"\n== L9-02 answerer 复现 (steps={len(steps)}, content={len(content)} chars) ==")

BASE = "http://127.0.0.1:8080/v1"
ANSWER_SYS = ("你是数据分析回答器。只依据给定的查询结果回答用户问题。"
              "规则: 第一行输出FINAL; 答案必须包含具体数字或文本结果; 数字不要用万/亿; "
              "按题目要求保留小数; 结果里没有的信息不要编造; 若结果是错误信息(error)则回答查询失败+原因。")
msgs = [{"role": "system", "content": ANSWER_SYS},
        {"role": "user", "content": content}]
for mx in (3000, 4500):
    body = {"model": "spark-x2.6-4b-lossless", "max_tokens": mx, "temperature": 0, "messages": msgs}
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", timeout=240,
                      headers={"Content-Type": "application/json"},
                      data=json.dumps(body))
    dt = time.time() - t0
    d = r.json()
    m = d["choices"][0].get("message", {})
    u = d.get("usage", {})
    print(f"mx={mx} [{dt:.1f}s] usage={u}")
    print(f"  content={repr((m.get('content') or ''))[:150]}")
    print(f"  reasoning={repr((m.get('reasoning_content') or ''))[:150]}")
