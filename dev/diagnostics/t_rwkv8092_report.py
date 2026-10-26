# -*- coding: utf-8 -*-
"""RWKV 8092 修复版报告: 通过题 + 工具使用 + 失败形态"""
import glob
import json

IDS = open(r"eval\_spark_v12c_fails.txt", encoding="utf-8").read().strip().split(",")
if isinstance(IDS, str):
    IDS = IDS.split(",")
d = {c["case"]: c for c in json.load(open(r"eval\results\v12c_calcpy_all.json", encoding="utf-8"))}
print("pass:", [i for i in IDS if d[i]["answer_ok"]])
adopt = 0
for cid in IDS:
    files = glob.glob(rf"artifacts\trace\v12c_calcpy_{cid}.json")
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
print("adoption:", adopt, "/12")
