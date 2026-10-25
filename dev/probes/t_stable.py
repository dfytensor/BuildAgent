# -*- coding: utf-8 -*-
import sys
import time
sys.path.insert(0, "agent")
from common import client, MODEL_ID

ok = 0
for i in range(6):
    try:
        t0 = time.time()
        r = client().chat.completions.create(model=MODEL_ID, temperature=0, max_tokens=60,
            messages=[{"role": "user", "content": f"请原样重复数字: {i}2{i}"}])
        dt = time.time() - t0
        ok += 1
        print(f"{i}: {dt:.1f}s {repr((r.choices[0].message.content or '')[:40])}")
    except Exception as e:
        print(f"{i}: FAIL {type(e).__name__}")
print(f"探针: {ok}/6 成功")
