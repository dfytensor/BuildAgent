# -*- coding: utf-8 -*-
"""单臂质量审计: 基建标记 + 分层表 (用法: python audit_arm.py <results.json>)"""
import json
import sys
import collections

path = sys.argv[1] if len(sys.argv) > 1 else r"eval\results\spark_v9_on_full.json"
cases = json.load(open(path, encoding="utf-8"))
infra = collections.Counter()
for c in cases:
    a = json.dumps(c.get("answers", []), ensure_ascii=False)
    if "(worker崩溃)" in a:
        infra["worker崩溃"] += 1
    if "(回答失败)" in a:
        infra["含回答失败"] += 1
    if a.strip() in ('[""]', "[]"):
        infra["纯空答"] += 1
print(f"{path}  n={len(cases)}")
print("基建标记:", dict(infra) or "无")
by = collections.defaultdict(lambda: [0, 0, 0, 0])
for c in cases:
    k = (c["suite"], c["level"])
    by[k][0] += 1
    by[k][1] += 1 if c.get("answer_ok") else 0
    by[k][2] += 1 if c.get("tool_ok") else 0
    by[k][3] += 1 if c.get("exec_ok") else 0
print("\n套件 层级  n  答对   工具OK  执行OK")
for (s, lv) in sorted(by):
    n, ok, t, e = by[(s, lv)]
    print(f"{s:6s} L{lv}  {n:3d}  {ok/n*100:5.0f}%  {t/n*100:5.0f}%  {e/n*100:5.0f}%")
fail_mark = [c["case"] for c in cases if not c.get("answer_ok")
             and any(m in json.dumps(c.get("answers", []), ensure_ascii=False)
                     for m in ("回答失败", "worker崩溃", "agent异常"))]
print("\n失败且带基建标记:", fail_mark or "无")
