# -*- coding: utf-8 -*-
"""DeepSeek 21道失败逐题解剖: 题面/黄金/工具链/答案 + 跨模型对照"""
import json

ds = {c["case"]: c for c in json.load(open(r"eval\results\deepseek_full_merged.json", encoding="utf-8"))}
mm = {c["case"]: c for c in json.load(open(r"eval\results\archive\minimax_minimax-m3.1-flash_free_v9_scaffold_all_20261022_195835.json", encoding="utf-8"))}
sp = {c["case"]: c for c in json.load(open(r"eval\results\v11c_full.json", encoding="utf-8"))}
cases = json.load(open(r"eval\cases.json", encoding="utf-8"))
cmap = {}
for s, lst in cases.items():
    for c in lst:
        cmap[c["id"]] = c

fails = [k for k, v in ds.items() if not v.get("answer_ok")]
print(f"DeepSeek failures: {len(fails)}\n")
for cid in fails:
    c = cmap[cid]
    g = c.get("gold") or {}
    if c.get("turns"):
        g = c["turns"]["turns"][-1].get("gold") or {}
        q = " || ".join(t["q"] for t in c["turns"]["turns"])
    else:
        q = c["q"]
    mm_ok = "✓" if mm.get(cid, {}).get("answer_ok") else "✗"
    sp_ok = "✓" if sp.get(cid, {}).get("answer_ok") else "✗"
    print(f"== {cid} (L{c['level']}) | minimax:{mm_ok} spark:{sp_ok} | exec:{ds[cid].get('exec_ok')}")
    print(f"   Q: {q[:100]}")
    print(f"   GOLD: {json.dumps(g.get('values'), ensure_ascii=False)[:120]}")
    if g.get("ref_sql"):
        print(f"   REF: {g['ref_sql'][:130]}")
    ans = json.dumps(ds[cid].get("answers", []), ensure_ascii=False)
    print(f"   ANS: {ans[:200]}")
    try:
        tr = json.load(open(rf"artifacts\trace\v11_metric2_{cid}.json", encoding="utf-8"))
        for t in tr["trace"]:
            for s in t.get("steps", []):
                a = s.get("args", {}).get("args", {})
                r = s.get("result", {})
                print(f"   STEP {s.get('tool')}: {json.dumps(a, ensure_ascii=False)[:110]}")
                print(f"        ok={r.get('ok')} rows={str(r.get('rows'))[:90]} err={str(r.get('error'))[:60]}")
    except Exception as e:
        print("   (no trace)", type(e).__name__)
    print()
