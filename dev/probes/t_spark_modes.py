# -*- coding: utf-8 -*-
import sys
import json
sys.path.insert(0, "agent")
from common import client, MODEL_ID, EXTRA_BODY

# 变体A: enable_thinking=false
r = client().chat.completions.create(model=MODEL_ID, temperature=0, max_tokens=500,
    extra_body=EXTRA_BODY or None,
    messages=[{"role": "user", "content": "1+1等于几? 只回答数字"}])
m = r.choices[0].message
print("A(false) content:", repr((m.content or "")[:60]))
rc = getattr(m, "reasoning_content", None)
print("A(false) reasoning_content:", repr((rc or "")[:100]))
d = m.model_dump() if hasattr(m, "model_dump") else {}
print("A(false) keys:", list(d.keys()))

# 变体B: 不传 enable_thinking(默认思考)
r = client().chat.completions.create(model=MODEL_ID, temperature=0, max_tokens=900,
    messages=[{"role": "user", "content": "1+1等于几? 只回答数字"}])
m = r.choices[0].message
print("B(默认) content:", repr((m.content or "")[:60]))
rc = getattr(m, "reasoning_content", None)
print("B(默认) reasoning_content:", repr((rc or "")[:150]))

# 变体C: enable_thinking=true
r = client().chat.completions.create(model=MODEL_ID, temperature=0, max_tokens=900,
    extra_body={"enable_thinking": True},
    messages=[{"role": "user", "content": "1+1等于几? 只回答数字"}])
m = r.choices[0].message
print("C(true) content:", repr((m.content or "")[:60]))
rc = getattr(m, "reasoning_content", None)
print("C(true) reasoning_content:", repr((rc or "")[:150]))
