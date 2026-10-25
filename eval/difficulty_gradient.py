# -*- coding: utf-8 -*-
"""难度轴(SQL L1-L9 / pandas P1-P4) x 轮数轴(tool T1-T6) 的能力地形图
每层输出: 工具OK(协议) / 执行OK(落地) / 答对(语义); 并对比 v0/v4/v7 看迭代如何移动难度悬崖
"""
import json
from collections import defaultdict

BASE_LEVELS = {
    "sql": {1: "L1 单表单字段", 2: "L2 单表多字段", 3: "L3 +1条件", 4: "L4 多字段+1条件",
            5: "L5 多字段多条件", 6: "L6 多表", 7: "L7 多表+条件", 8: "L8 多表多字段", 9: "L9 多表聚合"},
    "pandas": {1: "P1 单算子", 2: "P2 双算子", 3: "P3 多算子多步", 4: "P4 出图"},
    "tool": {1: "T1 一轮一次", 2: "T2 一轮多次", 3: "T3 多轮每轮一次",
             4: "T4 相隔几轮引用", 5: "T5 连续多跳", 6: "T6 跨maxlen"},
}
VERSIONS = ["v0_bare", "v1_react_sql", "v2_schema", "v3_selfheal",
            "v4_sandbox", "v5_memory", "v6_router", "v7_general"]


def level_stats(agent, suite):
    d = json.load(open(rf"eval\results\{agent}_all.json", encoding="utf-8"))
    agg = defaultdict(lambda: {"n": 0, "tool": 0, "exec": 0, "acc": 0})
    for x in d:
        if x["suite"] != suite:
            continue
        a = agg[x["level"]]
        a["n"] += 1
        a["tool"] += 1 if x["tool_ok"] else 0
        a["exec"] += 1 if x["exec_ok"] else 0
        a["acc"] += 1 if x["answer_ok"] else 0
    return {lvl: {"tool": 100.0 * a["tool"] / a["n"],
                  "exec": 100.0 * a["exec"] / a["n"],
                  "acc": 100.0 * a["acc"] / a["n"],
                  "n": a["n"]}
            for lvl, a in agg.items()}


def print_ladder(agent, suite, levels):
    stats = level_stats(agent, suite)
    print(f"\n--- {agent} · {suite} 难度阶梯 ---")
    print(f"{'层级':<18}{'N':>3}{'工具OK':>8}{'执行OK':>8}{'答对':>8}")
    for lvl, name in levels.items():
        s = stats.get(lvl)
        if not s:
            print(f"{name:<18}{levels[lvl] and '':>3}{'-':>8}{'-':>8}{'-':>8}")
            continue
        print(f"{name:<18}{s['n']:>3}"
              f"{s['tool']:>7.0f}%{s['exec']:>7.0f}%{s['acc']:>7.0f}%")
    return stats


def cliff_row(agent, suite, levels, metric="acc"):
    """每层一格: 数值; 用于跨版本对比悬崖位置"""
    stats = level_stats(agent, suite)
    out = {}
    for lvl in levels:
        s = stats.get(lvl)
        out[lvl] = int(round(s[metric])) if s else None
    return out


def main():
    all_out = {}
    for suite, levels in BASE_LEVELS.items():
        print("=" * 60)
        print(f"套件: {suite}")
        print("=" * 60)
        # v7 完整三层指标
        print_ladder("v7_general", suite, levels)
        # 跨版本: 答对率悬崖对比
        print(f"\n[{suite}] 跨版本答对率(%) — 迭代把悬崖推到哪了:")
        hdr = f"{'层级':<18}" + "".join(f"{v.split('_')[0]:>8}" for v in VERSIONS)
        print(hdr)
        table = {}
        for v in VERSIONS:
            table[v] = cliff_row(v, suite, levels)
        for lvl, name in levels.items():
            row = f"{name:<18}"
            for v in VERSIONS:
                val = table[v].get(lvl)
                row += (f"{val:>7}%" if val is not None else f"{'-':>8}")
            print(row)
        all_out[suite] = {v: table[v] for v in VERSIONS}

    with open(r"eval\results\difficulty_turn_gradient.json", "w", encoding="utf-8") as f:
        json.dump(all_out, f, ensure_ascii=False, indent=1)
    print("\nsaved -> eval/results/difficulty_turn_gradient.json")


if __name__ == "__main__":
    main()
