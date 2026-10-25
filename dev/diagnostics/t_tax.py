# -*- coding: utf-8 -*-
"""spark全量失败归因扫描:
1) SQL失败题的 trace SQL 是否含 year/month=裸数字(TEXT列陷阱)
2) 各套件 exec失败/答错分布
"""
import json
import re

cases = json.load(open(r"eval\results\v9_scaffold_all.json", encoding="utf-8"))
year_trap = re.compile(r"\b(year|month|day)\s*=\s*(20\d{2}|\d{1,2})\b")

stats = {"sql_fail": 0, "sql_fail_year_trap": 0, "sql_exec_fail": 0, "sql_exec_fail_year_trap": 0}
detail = []
for c in cases:
    if c["suite"] != "sql":
        continue
    bad = not c.get("answer_ok")
    exbad = not c.get("exec_ok")
    tr = None
    try:
        tr = json.load(open(rf"artifacts\trace\v9_scaffold_{c['case']}.json", encoding="utf-8"))
    except Exception:
        pass
    sqls = []
    if tr:
        for t in tr.get("trace", []):
            for s in t.get("steps", []):
                a = s.get("args", {}).get("args", {})
                if isinstance(a, dict) and a.get("sql"):
                    sqls.append(a["sql"])
    hit = any(year_trap.search(s) for s in sqls)
    if bad:
        stats["sql_fail"] += 1
        if hit:
            stats["sql_fail_year_trap"] += 1
        detail.append((c["case"], c.get("exec_ok"), hit, json.dumps(c.get("answers", []), ensure_ascii=False)[:50]))
    if exbad:
        stats["sql_exec_fail"] += 1
        if hit:
            stats["sql_exec_fail_year_trap"] += 1

print("SQL统计:", stats)
print("\n失败题(year陷阱=?)")
for d in detail:
    print(f"  {d[0]} exec={d[1]} year_trap={d[2]} 答={d[3]}")
