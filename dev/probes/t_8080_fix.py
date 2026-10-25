# -*- coding: utf-8 -*-
"""8080 思考开关实验: 重现回答器空+测 enable_thinking 形状"""
import requests
import json
import time

BASE = "http://127.0.0.1:8080/v1"

ANSWER_SYS = ("你是数据分析回答器。只依据给定的查询结果回答用户问题。"
              "规则: 第一行输出FINAL; 答案必须包含具体数字; 数字不要用万/亿。")
rows = json.dumps({"columns": ["label", "value"],
                   "rows": [["家居", 6927639.05], ["家电", 7282993.18], ["数码", 3404683.9],
                            ["服饰", 859845.62], ["食品", 838644], ["美妆", 980552.66]]},
                  ensure_ascii=False)
msgs = [{"role": "system", "content": ANSWER_SYS},
        {"role": "user", "content": f"用户问题: 各类目销售额是多少?\n[工具1结果] {rows}"}]

def call(extra=None, mx=700, tag=""):
    body = {"model": "spark-x2.6-4b-lossless", "max_tokens": mx,
            "temperature": 0, "messages": msgs}
    if extra:
        body.update(extra)
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", timeout=180,
                      headers={"Content-Type": "application/json"},
                      data=json.dumps(body))
    dt = time.time() - t0
    if r.status_code != 200:
        return f"[{dt:.1f}s] HTTP {r.status_code}: {r.text[:120]}"
    d = r.json()
    m = d["choices"][0].get("message", {})
    rc = repr((m.get("reasoning_content") or ""))[:50]
    print(f"[{tag}] [{dt:.1f}s] content={repr((m.get('content') or ''))[:80]}")
    print(f"    reasoning={rc} usage={d.get('usage', {}).get('completion_tokens')}")

print("== 1. 思考默认 + 700(重现) ==")
print(call(tag="default700"))
print("== 2. chat_template_kwargs.enable_thinking=false ==")
print(call({"chat_template_kwargs": {"enable_thinking": False}}, 700, "off-kw"))
print("== 3. top-level.enable_thinking=false(兼容形状) ==")
print(call({"enable_thinking": False}, 700, "off-top"))
print("== 4. 思考默认 + 2000(若关闭失败则用加预算验证) ==")
print(call(None, 2000, "default2000"))
