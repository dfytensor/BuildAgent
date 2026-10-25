# -*- coding: utf-8 -*-
"""首token丢失 A/B: 8012(step-graph+bf16) vs 8021(streaming+bf16)"""
import json
import time
import urllib.request

QS = ["请原样重复这五个字母: ABCDE",
      "1+1等于几? 只回答数字",
      "写一句以'春风'开头的诗"]
PORTS = [8012, 8021]


def ask(port, q, mx=100, temp=0.0, stream=False):
    body = json.dumps({"model": "m", "stream": stream, "max_tokens": mx,
                       "temperature": temp,
                       "messages": [{"role": "user", "content": q}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    if stream:
        chunks = []
        for raw in urllib.request.urlopen(req, timeout=120):
            line = raw.decode("utf-8").strip()
            if line.startswith("data: ") and line != "data: [DONE]":
                d = json.loads(line[6:])
                delta = d["choices"][0].get("delta") or {}
                if delta.get("content"):
                    chunks.append(delta["content"])
        return "".join(chunks), time.time() - t0
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    return r["choices"][0].message.content or "", time.time() - t0


for port in PORTS:
    print(f"===== port {port} =====")
    for q in QS:
        for stream in (False, True):
            try:
                t, dt = ask(port, q, stream=stream)
                print(f"  [{'流式' if stream else '非流式'}] {q[:18]} -> {repr(t[:60])} ({dt:.1f}s)")
            except Exception as e:
                print(f"  [{'流式' if stream else '非流式'}] {q[:18]} FAIL {type(e).__name__} {str(e)[:60]}")
