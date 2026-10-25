# -*- coding: utf-8 -*-
"""统计 query_metric 在最近全量跑批中的实际调用率(按套件)"""
import glob
import json
import collections

usage = collections.Counter()
cases_with = collections.Counter()
calls_by_case = collections.defaultdict(int)
scanned = 0
for p in glob.glob(r"artifacts\trace\v9_scaffold_*.json"):
    cid = p.split("v9_scaffold_")[-1].replace(".json", "")
    suite = cid.split("-")[0]
    try:
        tr = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    scanned += 1
    n_qm = 0
    for t in tr.get("trace", []):
        for s in t.get("steps", []):
            tool = s.get("tool") or (s.get("args", {}) or {}).get("tool")
            if tool == "query_metric":
                n_qm += 1
    if n_qm:
        cases_with[suite] += 1
        calls_by_case[cid] = n_qm

print(f"扫描 trace: {scanned}")
print("含query_metric调用的用例(按套件):", dict(cases_with), "合计", sum(cases_with.values()))
print("query_metric 总调用次数:", sum(calls_by_case.values()))
print("用例明细:", dict(list(calls_by_case.items())[:20]))
