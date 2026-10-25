# -*- coding: utf-8 -*-
"""8080 深度探测: n_ctx/长提示/并发槽位"""
import requests
import json
import time
import concurrent.futures as cf

BASE = "http://127.0.0.1:8080/v1"

print("== /props ==")
try:
    r = requests.get("http://127.0.0.1:8080/props", timeout=10)
    print(r.text[:400])
except Exception as e:
    print("FAIL", type(e).__name__, str(e)[:60])

def chat(mx, content, n=None, model="spark-x2.6-4b"):
    body = {"model": model, "max_tokens": mx, "temperature": 0,
            "messages": [{"role": "user", "content": content}]}
    t0 = time.time()
    r = requests.post(f"{BASE}/chat/completions", timeout=180,
                      headers={"Content-Type": "application/json"},
                      data=json.dumps(body))
    dt = time.time() - t0
    if r.status_code != 200:
        return dt, f"HTTP {r.status_code}: {r.text[:150]}"
    m = r.json()["choices"][0].get("message", {})
    return dt, repr((m.get("content") or ""))[:60]

print("\n== 长提示压力(~3300 tokens中文+工具琗) ==")
long_q = ("这是一个数据库分析任务。" * 100) + "\n请只回答 一个字: 好"
dt, out = chat(50, long_q)
print(f"[{dt:.1f}s] {out}")

print("\n== 并发2槽测试 ==")
with cf.ThreadPoolExecutor(2) as ex:
    fs = [ex.submit(chat, 30, "1+1等于几? 只回答数字") for _ in range(2)]
    t0 = time.time()
    for f in fs:
        dt2, out = f.result()
        print(f"  [{dt2:.1f}s] {out}")
print(f"总耗时 {time.time()-t0:.1f}s (若远小于2*单次, 说明2+槽)")
