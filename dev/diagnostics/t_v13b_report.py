# -*- coding: utf-8 -*-
"""v13b 报告: 通过题 + load_df/run_python 采纳率"""
import glob
import json

IDS = ["SQL-L3-06", "SQL-L4-02", "SQL-L4-03", "SQL-L4-05", "SQL-L5-02", "SQL-L6-02",
       "SQL-L6-03", "SQL-L8-01", "SQL-L8-05", "PY-P2-14", "PY-P2-15", "PY-P3-09",
       "PY-P3-11", "PY-P3-14", "PY-P3-15", "PY-P4-07", "TOOL-T3-05", "TOOL-T4-07"]

v13b = {c["case"]: c for c in json.load(open(r"eval\results\v13b_hybrid2_all.json", encoding="utf-8"))}
v12 = {c["case"]: c for c in json.load(open(r"eval\results\v12_views_all.json", encoding="utf-8"))}
v13 = {c["case"]: c for c in json.load(open(r"eval\results\v13_hybrid_all.json", encoding="utf-8"))}

print("v12 pass:", [i for i in IDS if v12[i]["answer_ok"]])
print("v13 pass:", [i for i in IDS if v13[i]["answer_ok"]])
print("v13b pass:", [i for i in IDS if v13b[i]["answer_ok"]])
print("v13b only:", [i for i in IDS if v13b[i]["answer_ok"] and not v12[i]["answer_ok"]])

adopt = 0
print("\ncase            load_df run_python sqlite  pass")
for cid in IDS:
    files = glob.glob(rf"artifacts\trace\v13b_hybrid2_{cid}.json")
    counts = {}
    if files:
        tr = json.load(open(files[0], encoding="utf-8"))
        for t in tr.get("trace", []):
            for s in t.get("steps", []):
                k = s.get("tool")
                counts[k] = counts.get(k, 0) + 1
    used = counts.get("load_df", 0) > 0 and counts.get("run_python", 0) > 0
    adopt += 1 if used else 0
    print(f"{cid:14s} {counts.get('load_df',0):6d} {counts.get('run_python',0):9d} {counts.get('sqlite_query',0):6d}  "
          f"{'OK' if v13b[cid]['answer_ok'] else 'X'}{'  [hybrid]' if used else ''}")
print(f"\n采纳率(load_df+run_python): {adopt}/{len(IDS)} = {adopt/len(IDS)*100:.0f}%")
