# -*- coding: utf-8 -*-
"""口径类双错题回收检查: v10(语义层) vs 之前双错清单的逐题回收情况"""
import json
import sys
import glob

# 之前双错中的口径/粒度类代表题(诊断阶段归类)
CALIBER = ["PY-P1-02", "PY-P1-04", "PY-P1-05", "PY-P2-02", "PY-P2-03", "PY-P2-10",
           "PY-P2-13", "PY-P3-01", "PY-P3-04", "PY-P3-05", "PY-P3-08", "PY-P3-09",
           "TOOL-T1-05", "TOOL-T2-03", "TOOL-T3-01", "TOOL-T3-02", "TOOL-T3-03", "TOOL-T3-05"]
label = sys.argv[1] if len(sys.argv) > 1 else "minimax_minimax-m3.1-flash_free_v9_scaffold_all_20261022_182222.json"
fs = sorted(glob.glob(r"eval\results\archive\*.json"), key=lambda p: __import__("os").path.getmtime(p))
src = None
for f in fs:
    if label.split("_")[0] in f or label == f:
        src = f
if src is None:
    src = label if label.endswith(".json") else fs[-1]
d = {x["case"]: x for x in json.load(open(src, encoding="utf-8"))}
print("数据源:", src)
print(f"\n{'用例':<12}{'之前':>6}{'本次':>6}  状态")
fixed = 0
for cid in CALIBER:
    if cid not in d:
        print(f"{cid:<12}{'?':>6}{'未跑':>6}")
        continue
    was = "错"  # 这些题此前在双错清单中
    now = "对" if d[cid]["answer_ok"] else "错"
    st = "✅收回" if now == "对" else "仍错"
    if now == "对":
        fixed += 1
    print(f"{cid:<12}{was:>6}{now:>6}  {st}")
print(f"\n口径类回收: {fixed}/{len(CALIBER)}")
