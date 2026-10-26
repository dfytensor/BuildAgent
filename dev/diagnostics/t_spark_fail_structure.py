# -*- coding: utf-8 -*-
"""4B(v11d/v1.1) 35道失败的结构分析: 单轮vs多轮/层级/跨轮中间错"""
import json
import collections

sp = {c["case"]: c for c in json.load(open(r"eval\results\v11d_context_all.json", encoding="utf-8"))}
cases = json.load(open(r"eval\cases.json", encoding="utf-8"))
cmap = {}
for s, lst in cases.items():
    for c in lst:
        cmap[c["id"]] = c

fails = [i for i, c in sp.items() if not c.get("answer_ok")]
print(f"总失败: {len(fails)}\n")

def is_multi(cid):
    return bool(cmap[cid].get("turns"))

single = [i for i in fails if not is_multi(i)]
multi = [i for i in fails if is_multi(i)]
print(f"单轮失败: {len(single)}")
print(f"多轮失败: {len(multi)} -> {multi}\n")

print("== 单轮失败按套件/层级 ==")
by = collections.Counter((cmap[i]["id"].split("-")[0], cmap[i]["level"]) for i in single)
for (s, lv), n in sorted(by.items()):
    print(f"  {s}-L{lv}: {n}")

print("\n== 多轮套件的整体表现(含中间轮) ==")
for suite in ("TOOL",):
    ids = [i for i in cmap if i.startswith(suite + "-") and is_multi(i)]
    ok_final = sum(1 for i in ids if sp[i].get("answer_ok"))
    ok_all = sum(1 for i in ids if sp[i].get("all_turns_ok"))
    only_final = [i for i in ids if sp[i].get("answer_ok") and not sp[i].get("all_turns_ok")]
    print(f"  多轮共{len(ids)}: 末轮对 {ok_final} | 所有轮都对 {ok_all} | 中间轮错但末轮对 {len(only_final)}: {only_final}")

print("\n== 35道失败明细 ==")
for i in fails:
    c = cmap[i]
    ans = json.dumps(sp[i].get("answers", []), ensure_ascii=False)
    turns = len(c["turns"]["turns"]) if c.get("turns") else 1
    print(f"{i} L{c['level']} turns={turns}")
    print(f"   Q: {c['q'][:70]}")
    print(f"   A: {ans[:110]}")
    g = c.get("gold") or (c["turns"]["turns"][-1].get("gold") if c.get("turns") else None) or {}
    print(f"   G: {json.dumps(g.get('values'), ensure_ascii=False)[:90]}")
