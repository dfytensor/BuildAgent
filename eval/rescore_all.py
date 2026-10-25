# -*- coding: utf-8 -*-
"""判分器修复: 嵌套黄金值递归展平 + 全历史结果离线重打分"""
import json

# ---- 1. checker 修复 ----
p = pathlib_ck = r"eval\checker.py"
t = open(p, encoding="utf-8").read()
if "_flatten_gold" not in t:
    anchor = "def match_values(gold_values, text):"
    fix = '''def _flatten_gold(vals):
    out = []
    for v in vals:
        if isinstance(v, (list, tuple)):
            out.extend(_flatten_gold(list(v)))
        else:
            out.append(v)
    return out


def match_values(gold_values, text):
    gold_values = _flatten_gold(gold_values)'''
    assert anchor in t
    t = t.replace(anchor, fix)
    open(p, "w", encoding="utf-8").write(t)
    print("checker: _flatten_gold added")
else:
    print("checker already fixed")

import sys
sys.path.insert(0, "eval")
import importlib
import checker
importlib.reload(checker)
from checker import match_values, chart_file_ok  # noqa

# ---- 2. 全历史重打分 ----
import os
cases = {x["id"]: x for lst in json.load(open(r"eval\cases.json", encoding="utf-8")).values() for x in lst}
BAD = ("回答失败", "LLM调用失败", "ConnectionError", "APIConnectionError")

FILES = {
    "minimax-v9": r"v9_scaffold_all.json",
    "2B": r"archive\minicpm5-2b_v7_general_all.json",
    "1B-16valid": r"archive\1B-bf16_v7_general_all_16case_valid.json",
    "v6-量化1B": r"v6_router_all.json",
    "run1-mixed": r"archive\minimax_m3_1_flash_v7_general_all_run1_mixed132.json",
}


def rescore(x):
    c = cases.get(x["case"])
    if c is None:
        return
    answers = x.get("answers", [])
    if c.get("turns"):
        turns = c["turns"]["turns"]
        ok_all, ans_ok = True, False
        for i, t in enumerate(turns):
            g = t["gold"]
            if g is None or (g.get("kind") == "chart"):
                continue
            if not g.get("values"):
                continue
            ans = answers[i] if i < len(answers) else ""
            ok, _ = match_values(g["values"], ans)
            ok_all = ok_all and ok
            if i == len(turns) - 1:
                ans_ok = ok
        x["all_turns_ok"] = ok_all and bool(answers)
        x["answer_ok"] = ans_ok and bool(answers)
    else:
        g = c.get("gold") or {}
        if g.get("kind") == "chart":
            pass  # chart_ok 保持原值(文件校验)
        else:
            ans = answers[0] if answers else ""
            ok, _ = match_values(g.get("values", []), ans)
            x["answer_ok"] = ok


for label, rel in FILES.items():
    fp = os.path.join(r"eval\results", rel) if not rel.startswith("archive") else os.path.join(r"eval\results", rel)
    if not os.path.exists(fp):
        print(f"{label}: 文件不存在 {fp}")
        continue
    d = json.load(open(fp, encoding="utf-8"))
    before = sum(1 for x in d if x["answer_ok"])
    for x in d:
        rescore(x)
    after = sum(1 for x in d if x["answer_ok"])
    json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{label}: 答对 {before} → {after} (共{len(d)})")

import os  # noqa
