# -*- coding: utf-8 -*-
"""按轮数/依赖深度的能力梯度视图"""
import json

d = json.load(open(r"eval\results\gradient_by_level.json", encoding="utf-8"))
versions = ["v0_bare", "v1_react_sql", "v2_schema", "v3_selfheal",
            "v4_sandbox", "v5_memory", "v6_router", "v7_general"]
names = {
    "tool-L1": "T1 一轮一次tool",
    "tool-L2": "T2 一轮多次tool",
    "tool-L3": "T3 多轮·每轮一次",
    "tool-L4": "T4 相隔几轮引用",
    "tool-L5": "T5 连续多跳依赖",
    "tool-L6": "T6 跨maxlen(6-9轮)",
}
print("=== 工具套件: 按轮数/依赖深度梯度 (最终答对率) ===")
hdr = f"{'层级':<22}" + "".join(f"{v.split('_')[0]:>9}" for v in versions)
print(hdr)
for k in ["tool-L1", "tool-L2", "tool-L3", "tool-L4", "tool-L5", "tool-L6"]:
    row = f"{names[k]:<22}"
    for v in versions:
        val = d.get(v, {}).get(k, "-")
        row += f"{val:>9}"
    print(row)

print()
print("=== SQL 套件: 按复杂度层级 L1-L9 (v7) ===")
for i in range(1, 10):
    k = f"sql-L{i}"
    print(f"  {k}: {d.get('v7_general', {}).get(k, '-')}")
print()
print("=== pandas 套件: P1-P4 (v7) ===")
for i in range(1, 5):
    k = f"pandas-L{i}"
    print(f"  {k}: {d.get('v7_general', {}).get(k, '-')}")
