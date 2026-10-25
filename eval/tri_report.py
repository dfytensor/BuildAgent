# -*- coding: utf-8 -*-
"""三模型(1B/2B/minimax)同尺汇总: 读归档, 产出 总表+四象限+层级地形"""
import json
import glob
import os
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(BASE, "eval", "results", "archive")


def load_any(pattern, exact=None):
    if exact:
        p = os.path.join(ARCH, exact)
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    fs = sorted(glob.glob(os.path.join(ARCH, pattern)), key=os.path.getmtime)
    return json.load(open(fs[-1], encoding="utf-8")) if fs else None


def summarize(d, label):
    if not d:
        print(f"{label}: 无数据")
        return None
    n = len(d)
    t = 100 * sum(x["tool_ok"] for x in d) / n
    e = 100 * sum(x["exec_ok"] for x in d) / n
    a = 100 * sum(x["answer_ok"] for x in d) / n
    suites = defaultdict(lambda: [0, 0])
    for x in d:
        suites[x["suite"]][0] += 1
        suites[x["suite"]][1] += x["answer_ok"]
    s_txt = " ".join(f"{k}:{100*v[1]/v[0]:.0f}%" for k, v in sorted(suites.items()))
    print(f"{label:<14} N={n:<4} 工具{t:.1f}% 执行{e:.1f}% 答对{a:.1f}%  [{s_txt}]")
    return {x["case"]: x for x in d}


m1 = load_any("1B-bf16_v7_general_all_16case_valid.json")
m2 = load_any("minicpm5-2b_v7_general_all.json")
m3 = load_any(None, exact="minimax_minimax-m3.1-flash_free_v9_scaffold_all_20261022_195835.json")

print("=" * 76)
print("同尺对照(答对率, 尺=150阶梯用例; 各模型取已完成部分):")
d1 = summarize(m1, "1B-bf16")
d2 = summarize(m2, "2B-bf16")
d3 = summarize(m3, "minimax-m3.1-flash")

# 四象限(取共同用例, 以 2B 为参照)
if d1 and d2:
    common = sorted(set(d1) & set(d2))
    q = defaultdict(list)
    for c in common:
        a, b = d1[c]["answer_ok"], d2[c]["answer_ok"]
        q["both_ok" if a and b else "both_bad" if not a and not b else "only_1B" if a else "only_2B"].append(c)
    print(f"\n1B vs 2B 四象限 (共同 {len(common)} 题):")
    for k in ("both_ok", "only_2B", "only_1B", "both_bad"):
        print(f"  {k:<9} {len(q[k]):>3}  {sorted(q[k])[:8]}{'...' if len(q[k])>8 else ''}")
if d2 and d3:
    common = sorted(set(d2) & set(d3))
    q = defaultdict(list)
    for c in common:
        a, b = d2[c]["answer_ok"], d3[c]["answer_ok"]
        q["both_ok" if a and b else "both_bad" if not a and not b else "only_2B" if a else "only_minimax"].append(c)
    print(f"\n2B vs minimax 四象限 (共同 {len(common)} 题):")
    for k in ("both_ok", "only_minimax", "only_2B", "both_bad"):
        print(f"  {k:<12} {len(q[k]):>3}  {sorted(q[k])[:8]}{'...' if len(q[k])>8 else ''}")
