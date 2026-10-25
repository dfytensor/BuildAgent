# -*- coding: utf-8 -*-
"""验证: L5-02/L9-02 真提示 + answerer 关思考 -> 应该秒出FINAL"""
import json
import requests
import time

trace = json.load(open(r"artifacts\trace\v9_scaffold_SQL-L9-02.json", encoding="utf-8"))
user = trace["trace"][0]["user"]
steps = trace["trace"][0]["steps"]
content = f"用户问题: {user}"
for i, st in enumerate(steps):
    content += f"\n[工具{i+1}结果] {json.dumps(st['result'], ensure_ascii=False)[:900]}"

ANSWER_SYS = ("你是数据分析回答器。只依据给定的查询结果回答用户问题。"
              "规则: 第一行输出FINAL; 答案必须包含具体数字或文本结果; 数字不要用万/亿; "
              "按题目要求保留小数; 结果里没有的信息不要编造; 若结果是错误信息(error)则回答查询失败+原因。")

BASE = "http://127.0.0.1:8080/v1"
msgs = [{"role": "system", "content": ANSWER_SYS},
        {"role": "user", "content": content}]

for tag, extra in (("off", {"chat_template_kwargs": {"enable_thinking": False}}),):
    body = {"model": "spark-x2.6-4b-lossless", "max_tokens": 1500, "temperature": 0,
            "messages": msgs}
    body.update(extra)
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", timeout=240,
                      headers={"Content-Type": "application/json"},
                      data=json.dumps(body))
    dt = time.time() - t0
    d = r.json()
    m = d["choices"][0].get("message", {})
    print(f"[{tag}] [{dt:.1f}s] usage={d.get('usage')}")
    print(f"  content={repr((m.get('content') or ''))[:250]}")
