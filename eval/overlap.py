# -*- coding: utf-8 -*-
"""四象限重叠分析: 两份同尺逐题结果(不同模型/版本)的正确-错误分布对比
A独对=旧模型抖动或脚手架差异; B独对=新模型/新机制解锁区; 双错=超界区(微调/约束化靶子)
用法: python eval/overlap.py --a results/A.json --b results/B.json --la 1B量化 --lb 2B [--save out.json]
"""
import os
import json
import argparse
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(p):
    if not os.path.exists(p):
        alt = os.path.join(BASE, "eval", "results", "archive", os.path.basename(p))
        if os.path.exists(alt):
            p = alt
    with open(p, encoding="utf-8") as f:
        return {x["case"]: x for x in json.load(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--la", default="A")
    ap.add_argument("--lb", default="B")
    ap.add_argument("--metric", default="answer_ok", choices=["answer_ok", "exec_ok", "all_turns_ok"])
    ap.add_argument("--save", default="")
    args = ap.parse_args()

    A, B = load(os.path.join(BASE, "eval", "results", args.a)), load(os.path.join(BASE, "eval", "results", args.b))
    common = sorted(set(A) & set(B))
    quad = {"both_ok": [], "both_bad": [], f"only_{args.la}": [], f"only_{args.lb}": []}
    for cid in common:
        a, b = bool(A[cid][args.metric]), bool(B[cid][args.metric])
        if a and b:
            quad["both_ok"].append(cid)
        elif not a and not b:
            quad["both_bad"].append(cid)
        elif a:
            quad[f"only_{args.la}"].append(cid)
        else:
            quad[f"only_{args.lb}"].append(cid)

    n = len(common)
    print(f"共同用例 {n} | 指标 {args.metric}")
    for k, v in quad.items():
        print(f"  {k:<16} {len(v):>3} ({100*len(v)/n:.0f}%)")

    # 按套件×层级分解四象限(重点看解锁区/超界区落在哪)
    dist = defaultdict(lambda: defaultdict(int))
    def key(cid):
        p = cid.split("-")
        return f"{ {'SQL':'sql','PY':'pandas','TOOL':'tool'}.get(p[0], p[0]) }-L{p[1].lstrip('LTPY')[:1] if False else cid.split('-')[1][1:]}"
    for k, cids in quad.items():
        for cid in cids:
            suite = {"SQL": "sql", "PY": "pandas", "TOOL": "tool"}.get(cid.split("-")[0], "?")
            dist[f"{suite}-L{cid.split('-')[1][1:]}"][k] += 1
    print("\n层级分布(仅列出含 非重叠 的层级):")
    for k in sorted(dist):
        q = dist[k]
        if q.get(f"only_{args.la}", 0) or q.get(f"only_{args.lb}", 0):
            print(f"  {k:<10} {dict(q)}")

    print("\n解锁区明细(仅B独对 = {}):".format(args.lb))
    for cid in quad[f"only_{args.lb}"]:
        print("  ", cid)
    print("退化区明细(仅A独对 = {}):".format(args.la))
    for cid in quad[f"only_{args.la}"]:
        print("  ", cid)

    if args.save:
        out = os.path.join(BASE, "eval", "results", args.save)
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"n": n, "metric": args.metric, "quads": {k: v for k, v in quad.items()},
                       "by_level": {k: dict(v) for k, v in dist.items()}}, f, ensure_ascii=False, indent=1)
        print("saved ->", out)


if __name__ == "__main__":
    main()
