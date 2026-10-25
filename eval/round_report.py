# -*- coding: utf-8 -*-
"""轮次报告: 上一版 vs 当前版
用法: python eval/round_report.py <prev.json> <cur.json> [标签A] [标签B]
输出: 套件对比 / 四象限 / 新修好 / 新弄坏 / 当前失败分类
"""
import json
import sys
import collections

prev_p, cur_p = sys.argv[1], sys.argv[2]
la = sys.argv[3] if len(sys.argv) > 3 else "prev"
lb = sys.argv[4] if len(sys.argv) > 4 else "cur"
prev = {c["case"]: c for c in json.load(open(prev_p, encoding="utf-8"))}
cur = {c["case"]: c for c in json.load(open(cur_p, encoding="utf-8"))}
ids = [k for k in cur if k in prev]


def suite_table(d, label):
    by = collections.defaultdict(lambda: [0, 0])
    for c in d.values():
        by[c["suite"]][1] += 1
        by[c["suite"]][0] += 1 if c.get("answer_ok") else 0
    parts = []
    for s in ("sql", "pandas", "tool"):
        if by[s][1]:
            parts.append(f"{s} {by[s][0]}/{by[s][1]}={by[s][0]/by[s][1]*100:.0f}%")
    tot_ok = sum(1 for c in d.values() if c.get("answer_ok"))
    tot_n = len(d)
    print(f"{label}: " + " | ".join(parts) + f" | 合计 {tot_ok}/{tot_n} = {tot_ok/tot_n*100:.1f}%")


suite_table(prev, la)
suite_table(cur, lb)

quad = collections.Counter()
for k in ids:
    a, b = prev[k].get("answer_ok"), cur[k].get("answer_ok")
    quad[(a, b)] += 1
both_ok, both_bad = quad[(True, True)], quad[(False, False)]
only_a, only_b = quad[(True, False)], quad[(False, True)]
print(f"\n四象限: 双对 {both_ok} | 双错 {both_bad} | 仅{la} {only_a} | 仅{lb} {only_b}")
fixed = [k for k in ids if not prev[k].get("answer_ok") and cur[k].get("answer_ok")]
broke = [k for k in ids if prev[k].get("answer_ok") and not cur[k].get("answer_ok")]
print(f"新修好({len(fixed)}): {fixed}")
print(f"新弄坏({len(broke)}): {broke}")

cats = collections.Counter()
for k in ids:
    c = cur[k]
    if c.get("answer_ok"):
        continue
    a = json.dumps(c.get("answers", []), ensure_ascii=False)
    if not c.get("tool_ok"):
        cats["无工具/规划失败"] += 1
    elif any(x in a for x in ("0行", "为空", "无数据", "未查询到")):
        cats["空结果类"] += 1
    elif any(x in a for x in ("未提供", "不完整", "缺失", "无法列出")):
        cats["信息缺失类"] += 1
    else:
        cats["语义/其他"] += 1
print("当前失败分类:", dict(cats))
