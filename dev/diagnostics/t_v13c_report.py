# -*- coding: utf-8 -*-
"""v13c 报告: 通过题 + 采纳率"""
import glob
import json

IDS = ["SQL-L3-06", "SQL-L4-02", "SQL-L4-03", "SQL-L4-05", "SQL-L5-02", "SQL-L6-02",
       "SQL-L6-03", "SQL-L8-01", "SQL-L8-05", "PY-P2-14", "PY-P2-15", "PY-P3-09",
       "PY-P3-11", "PY-P3-14", "PY-P3-15", "PY-P4-07", "TOOL-T3-05", "TOOL-T4-07"]
d = {c["case"]: c for c in json.load(open(r"eval\results\v13c_gated_all.json", encoding="utf-8"))}
print("pass:", [i for i in IDS if d[i]["answer_ok"]])
adopt = 0
for cid in IDS:
    files = glob.glob(rf"artifacts\trace\v13c_gated_{cid}.json")
    cnt = {}
    if files:
        tr = json.load(open(files[0], encoding="utf-8"))
        for t in tr.get("trace", []):
            for s in t.get("steps", []):
                cnt[s.get("tool")] = cnt.get(s.get("tool"), 0) + 1
    used = cnt.get("load_df", 0) > 0 and cnt.get("run_python", 0) > 0
    adopt += 1 if used else 0
    mark = "OK" if d[cid]["answer_ok"] else "X"
    print(f"{cid:14s} load_df={cnt.get('load_df',0)} py={cnt.get('run_python',0)} "
          f"sql={cnt.get('sqlite_query',0)} {mark}{'  [hybrid]' if used else ''}")
print("adoption:", adopt, "/18")
