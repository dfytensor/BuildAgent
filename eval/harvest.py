# -*- coding: utf-8 -*-
"""从 trace 文件收割结果到 results json(断点续跑加速)"""
import os
import sys
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "eval"))
from checker import score_case  # noqa

TRACE_DIR = os.path.join(BASE, "artifacts", "trace")


def harvest(agent_name, suite="all"):
    with open(os.path.join(BASE, "eval", "cases.json"), encoding="utf-8") as f:
        CASES = json.load(f)
    by_id = {c["id"]: c for lst in CASES.values() for c in lst}

    out_path = os.path.join(BASE, "eval", "results", f"{agent_name}_{suite}.json")
    details = []
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            details = json.load(f)
    have = {d["case"] for d in details}
    added = 0
    for c in by_id.values():
        if suite != "all" and not c["id"].lower().startswith(suite[:3].lower()):
            pass
        cid = c["id"]
        if cid in have:
            continue
        tp = os.path.join(TRACE_DIR, f"{agent_name}_{cid}.json")
        if not os.path.exists(tp):
            continue
        try:
            with open(tp, encoding="utf-8") as f:
                tr = json.load(f)
            answers = [t["answer"] for t in tr["trace"]]
            n_calls = sum(len(t["steps"]) for t in tr["trace"])
            exec_errors = sum(1 for t in tr["trace"] for s in t["steps"] if not s["result"].get("ok", False))
            # 异常答案不算完成
            if answers and "(agent异常" in answers[0]:
                continue
            m = score_case(c, {"answers": answers, "n_tool_calls": n_calls, "exec_errors": exec_errors}, agent_name)
            m["answers"] = answers
            details.append(m)
            added += 1
        except Exception as e:
            print(f"skip {cid}: {e}")
    order = {cid: i for i, cid in enumerate(by_id)}
    details.sort(key=lambda d: order.get(d["case"], 9999))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=1)
    print(f"{agent_name}: harvested {added}, total {len(details)} -> {out_path}")


if __name__ == "__main__":
    harvest(sys.argv[1] if len(sys.argv) > 1 else "v0_bare")
