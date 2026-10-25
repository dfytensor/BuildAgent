# -*- coding: utf-8 -*-
"""18题代表集三模型对照 + DeepSeek失败项"""
import json

REP = ["SQL-L1-01", "SQL-L1-03", "SQL-L3-02", "SQL-L5-02", "SQL-L9-02", "SQL-L9-05",
       "PY-P1-02", "PY-P2-09", "PY-P3-06", "PY-P4-02", "PY-P4-04",
       "TOOL-T1-05", "TOOL-T1-09", "TOOL-T2-01", "TOOL-T4-01", "TOOL-T4-08", "TOOL-T5-01", "TOOL-T6-01"]
ARMS = {
    "deepseek-flash v11c": r"eval\results\v11_metric2_all.json",
    "spark-4B v11c": r"eval\results\v11c_full.json",
    "spark-4B v9(基线)": r"eval\results\spark_v9_off_full.json",
    "minimax v9": r"eval\results\archive\minimax_minimax-m3.1-flash_free_v9_scaffold_all_20261022_195835.json",
}
for name, p in ARMS.items():
    d = {c["case"]: c for c in json.load(open(p, encoding="utf-8"))}
    ok = sum(1 for i in REP if d.get(i, {}).get("answer_ok"))
    fails = [i for i in REP if not d.get(i, {}).get("answer_ok")]
    print(f"{name}: {ok}/18 = {ok/18*100:.1f}%  失败: {fails}")
