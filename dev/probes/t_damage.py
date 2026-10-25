# -*- coding: utf-8 -*-
"""8000 bf16 部署损伤率量化: 20条简单QA"""
import sys
import json
import urllib.request

QS = ["1+1等于几?",
      "中国的首都是哪里?",
      "请原样重复: ABCDE",
      "2乘以3等于几?",
      "水的化学式是什么?",
      "说出一个中国的省份",
      "3,7,12哪个最大? 只答数字",
      "请重复单词: hello",
      "一年有几个月?",
      "天空是什么颜色? 一个词"]
empty, corrupted, ok = 0, 0, 0
samples = []
for i in range(2):
    for q in QS:
        body = json.dumps({"model": "minicpm5", "max_tokens": 60, "temperature": 0,
                           "messages": [{"role": "user", "content": q}]}).encode()
        req = urllib.request.Request("http://127.0.0.1:8000/v1/chat/completions",
                                     data=body, headers={"Content-Type": "application/json"})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            t = (r["choices"][0].get("message", {}) or {}).get("content") or ""
        except Exception as e:
            t = f"(EXC {type(e).__name__})"
        if t.strip() == "":
            empty += 1
            tag = "EMPTY"
        elif q == "请原样重复: ABCDE" and "ABCDE" not in t:
            corrupted += 1
            tag = "CORRUPT"
        else:
            ok += 1
            tag = "ok"
        samples.append(f"[{tag}] {q[:14]} -> {repr(t[:50])}")

print(f"总计{len(samples)}: ok={ok} empty={empty} corrupted={corrupted}  (损伤率={(empty+corrupted)*100//len(samples)}%)")
for s in samples:
    print(s)
