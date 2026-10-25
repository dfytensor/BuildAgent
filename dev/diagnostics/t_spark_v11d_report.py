# -*- coding: utf-8 -*-
"""spark v11d(v1.1) 报告: 总分/分层 + 13道修正题 vs 137道未改题 的分解归因"""
import json
import collections

sp_new = {c["case"]: c for c in json.load(open(r"eval\results\v11d_context_all.json", encoding="utf-8"))}
sp_old = {c["case"]: c for c in json.load(open(r"eval\results\v11c_full.json", encoding="utf-8"))}
ds = {c["case"]: c for c in json.load(open(r"eval\results\v11d_v11_full.json", encoding="utf-8"))}

CHANGED = {"SQL-L6-04", "SQL-L7-01", "SQL-L7-02", "PY-P1-02", "PY-P1-04", "PY-P2-02",
           "PY-P2-07", "PY-P2-13", "PY-P3-11", "PY-P3-15", "TOOL-T2-03", "TOOL-T4-03", "TOOL-T5-04"}


def score(d, ids=None):
    ids = ids if ids is not None else d.keys()
    ok = sum(1 for i in ids if d.get(i, {}).get("answer_ok"))
    return ok, len(list(ids))


def table(d, label):
    by = collections.defaultdict(lambda: [0, 0])
    for c in d.values():
        by[c["suite"]][1] += 1
        by[c["suite"]][0] += 1 if c.get("answer_ok") else 0
    parts = [f"{s} {by[s][0]}/{by[s][1]}={by[s][0]/by[s][1]*100:.0f}%" for s in ("sql", "pandas", "tool")]
    print(f"{label}: " + " | ".join(parts))


print("== 总分 ==")
table(sp_old, "spark v11c(v1.0)")
table(sp_new, "spark v11d(v1.1)")
o, n = score(sp_old)
print(f"spark v11c(v1.0): {o}/{n} = {o/n*100:.1f}%")
o, n = score(sp_new)
print(f"spark v11d(v1.1): {o}/{n} = {o/n*100:.1f}%")
o, n = score(ds)
print(f"deepseek v11d(v1.1): {o}/{n} = {o/n*100:.1f}%")

print("\n== 分解: 13道修正题 vs 137道未改题 ==")
for label, ids in (("13 changed", CHANGED), ("137 unchanged", set(sp_new) - CHANGED)):
    o1, n1 = score(sp_old, ids)
    o2, n2 = score(sp_new, ids)
    print(f"  {label}: v11c {o1}/{n1} -> v11d-v1.1 {o2}/{n2} ({o2-o1:+d})")

print("\n== vs deepseek(v1.1) 四象限 ==")
q = collections.Counter()
for i in sp_new:
    q[(sp_new[i].get("answer_ok"), ds.get(i, {}).get("answer_ok"))] += 1
print(f"  双对 {q[(True,True)]} | 双错 {q[(False,False)]} | 仅spark {q[(True,False)]} | 仅deepseek {q[(False,True)]}")

print("\n== spark v11d 失败清单 ==")
fails = [i for i, c in sp_new.items() if not c.get("answer_ok")]
print(len(fails), fails)
