# -*- coding: utf-8 -*-
"""双错区黄金答案执行审计:
对每道双错题: (1)重新执行黄金参考SQL/py, 验证黄金值与当前DB一致
             (2)执行模型实际发出的SQL, 对比模型结果集 vs 黄金结果集
判定: 黄金正确+模型错(真语义错) / 黄金正确+模型结果等价(判分/格式问题) / 黄金错误(评测bug)
"""
import json
import sqlite3
import re
import os

DB = r"data\shop.db"
BAD = json.load(open(r"eval\results\overlap_minimax_v9_vs_2b_final.json", encoding="utf-8"))["quads"]["both_bad"]
cases = {x["id"]: x for lst in json.load(open(r"eval\cases.json", encoding="utf-8")).values() for x in lst}
v9 = {x["case"]: x for x in json.load(open(r"eval\results\v9_scaffold_all.json", encoding="utf-8"))}
d2 = {x["case"]: x for x in json.load(open(r"eval\results\archive\minicpm5-2b_v7_general_all.json", encoding="utf-8"))}

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


def norm_rows(rows):
    """行规范化: 浮点round2, 元组排序(无序比较)"""
    out = []
    for r in rows:
        nr = tuple(round(c, 2) if isinstance(c, float) else c for c in r)
        out.append(nr)
    return sorted(out, key=repr)


def exec_sql(sql):
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = [tuple(r) for r in cur.fetchall()]
    return cols, rows


verdicts = {"黄金正确_模型错": [], "黄金正确_模型结果等价": [], "黄金错误": [], "无法审计": []}
report = []

for cid in sorted(BAD):
    c = cases[cid]
    g = c.get("gold") or {}
    entry = {"case": cid, "q": c["q"][:60]}
    if g.get("kind") == "chart":
        verdicts["无法审计"].append(cid)
        continue
    ref_sql = g.get("ref_sql")
    if not ref_sql:
        # gpy类: 用ref_py重算
        ref_py = g.get("ref_py")
        if not ref_py:
            verdicts["无法审计"].append(cid)
            report.append(f"{cid}: 无参考实现")
            continue
        import pandas as pd
        dfs = {t: pd.read_sql(f"SELECT * FROM {t}", conn) for t in
               ("customers", "products", "orders", "order_items")}
        loc = {"dfs": dfs, "pd": pd, "np": __import__("numpy")}
        try:
            vals = eval(ref_py, {"__builtins__": {}}, loc)
            gold_now = vals if isinstance(vals, list) else [vals]
        except Exception as e:
            verdicts["无法审计"].append(cid)
            report.append(f"{cid}: ref_py执行失败 {e}")
            continue
        gold_now = [round(v, 4) if isinstance(v, float) else v for v in gold_now]
        stored = g.get("values", [])
        entry["黄金重算"] = str(gold_now[:6])
        if json.dumps(gold_now, default=str) == json.dumps(stored, default=str):
            verdicts["黄金正确_模型错"].append(cid)  # 先入此桶, 后面再细分
        entry["_type"] = "py"
        report.append(json.dumps(entry, ensure_ascii=False))
        continue

    # ---- gsql 类: 重执行黄金SQL + 执行模型SQL ----
    try:
        gcols, grows = exec_sql(ref_sql)
    except Exception as e:
        verdicts["黄金错误"].append(cid)
        report.append(f"{cid}: 黄金SQL本身报错 {e}")
        continue
    gold_now = norm_rows(grows)
    stored_vals = g.get("values", [])
    # 黄金完整性: 存储值应能在重执行结果中找到(平铺匹配)
    flat = [v for r in gold_now for v in r]
    flat = [round(v, 2) if isinstance(v, float) else v for v in flat]
    stored_norm = [round(v, 2) if isinstance(v, float) else v for v in stored_vals]
    gold_ok = all(any(str(sv) == str(fv) for fv in flat) for sv in stored_norm) if stored_norm else True

    # 模型SQL(取v9 trace中最后一条成功的sqlite_query)
    msql, mrows, mcols = None, None, None
    tp = rf"artifacts\trace\v9_scaffold_{cid}.json"
    if os.path.exists(tp):
        tr = json.load(open(tp, encoding="utf-8"))
        for t in tr["trace"]:
            for s in t.get("steps", []):
                if s.get("tool") == "sqlite_query" and s["result"].get("ok") and s["result"].get("rows") is not None:
                    msql = s["args"].get("sql")
                    mcols = s["result"]["columns"]
                    mrows = [tuple(r) for r in s["result"]["rows"]]
    verdict = ""
    if not gold_ok:
        verdict = "黄金错误(重执行不一致)"
        verdicts["黄金错误"].append(cid)
    elif msql is None:
        verdict = "黄金正确_模型未出SQL"
        verdicts["黄金正确_模型错"].append(cid)
    else:
        try:
            mcols2, mrows2 = exec_sql(msql)
            m_now = norm_rows(mrows2)
            g_now = norm_rows(grows)
            if m_now == g_now:
                verdict = "黄金正确_模型SQL结果等价"
                verdicts["黄金正确_模型结果等价"].append(cid)
            else:
                verdict = "黄金正确_模型SQL结果不同"
                verdicts["黄金正确_模型错"].append(cid)
        except Exception as e:
            verdict = f"模型SQL执行失败: {str(e)[:40]}"
            verdicts["黄金正确_模型错"].append(cid)
    entry["verdict"] = verdict
    entry["gold_sql"] = ref_sql[:150]
    entry["model_sql"] = (msql or "")[:150]
    report.append(json.dumps(entry, ensure_ascii=False))

print("=== 双错区审计结果 ===")
for k, v in verdicts.items():
    print(f"  {k}: {len(v)}  {v[:12]}")
open(r"eval\_golden_audit.txt", "w", encoding="utf-8").write("\n".join(report))
print("明细 -> eval/_golden_audit.txt")
