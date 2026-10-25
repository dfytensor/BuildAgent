# -*- coding: utf-8 -*-
"""补充审计: gpy-zip类与多轮类的黄金验证 + 判分修复后的当前真实状态"""
import json
import sqlite3
import pandas as pd

DB = r"data\shop.db"
conn = sqlite3.connect(DB)

cases = {x["id"]: x for lst in json.load(open(r"eval\cases.json", encoding="utf-8")).values() for x in lst}
v9 = {x["case"]: x for x in json.load(open(r"eval\results\v9_scaffold_all.json", encoding="utf-8"))}
d2 = {x["case"]: x for x in json.load(open(r"eval\results\archive\minicpm5-2b_v7_general_all.json", encoding="utf-8"))}

AUDIT = ["PY-P1-04", "PY-P2-02", "PY-P2-03", "PY-P2-10", "PY-P2-13", "PY-P2-14",
         "PY-P3-01", "PY-P3-02", "PY-P3-03", "PY-P3-04",
         "TOOL-T3-01", "TOOL-T3-02", "TOOL-T3-03", "TOOL-T3-05", "TOOL-T3-06", "TOOL-T3-07"]

dfs = {t: pd.read_sql(f"SELECT * FROM {t}", conn) for t in ("customers", "products", "orders", "order_items")}

print("=== gpy/多轮类黄金验证(重执行参考实现 vs 存储黄金 vs 模型答案) ===")
for cid in AUDIT:
    c = cases[cid]
    if c.get("turns"):
        turns = c["turns"]["turns"]
        infos = []
        for t in turns:
            g = t["gold"]
            if g and g.get("ref_sql"):
                try:
                    cur = conn.execute(g["ref_sql"])
                    now = [list(r) for r in cur.fetchall()]
                    ok = json.dumps(now, default=str)[:60] == json.dumps([list(r) for r in [tuple(v) for v in [g["values"][i:i+2]]]][0][:0] or now, default=str)[:60]
                    infos.append(f"{now[:3]}")
                except Exception as e:
                    infos.append(f"ERR {e}")
            elif g and g.get("values"):
                infos.append(str(g["values"][:4]))
        print(f"{cid} 各轮黄金: {infos}")
        # 模型末答
        if cid in v9:
            print("   v9末答:", v9[cid]["answers"][-1][:100])
        continue
    g = c.get("gold", {})
    ref_py = g.get("ref_py")
    if not ref_py:
        print(f"{cid}: 无ref_py(可能是gsql, 跳过)")
        continue
    loc = {"dfs": dfs, "pd": pd, "np": __import__("numpy")}
    try:
        now = eval(ref_py, {"__builtins__": {}}, loc)
        now = [round(float(v), 4) if isinstance(v, (int, float)) else v for v in (now if isinstance(now, list) else [now])]
    except Exception as e:
        print(f"{cid} ref_py失败: {e}")
        continue
    stored = g.get("values", [])
    stored_n = [round(float(v), 4) if isinstance(v, (int, float)) else v for v in stored]
    match = json.dumps(now, default=str) == json.dumps(stored_n, default=str)
    a2 = (d2[cid]["answers"][-1] if cid in d2 else "")[:60]
    a9 = (v9[cid]["answers"][-1] if cid in v9 else "")[:60]
    print(f"{cid} 黄金重算={now[:4]} 存储={stored_n[:4]} 一致={match}")
    print(f"   2B: {a2}")
    print(f"   v9: {a9}")
