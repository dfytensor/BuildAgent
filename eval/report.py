# -*- coding: utf-8 -*-
"""汇总各版本评测结果 -> 能力梯度表(格物致知证据链)"""
import os
import json
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "eval", "results")

VERSIONS = ["v0_bare", "v1_react_sql", "v2_schema", "v3_selfheal",
            "v4_sandbox", "v5_memory", "v6_router", "v7_general", "v8_calculator"]
NOTES = {
    "v0_bare": "裸模型:无工具无schema无记忆",
    "v1_react_sql": "+ReAct工具循环+sqlite_query (能执行SQL拿真数据)",
    "v2_schema": "+库表schema注入 (SQL内容正确了,但暴露协议崩塌新缺陷)",
    "v3_selfheal": "+few-shot格式锚定+解析失败纠偏重试 (修复工具调用协议)",
    "v4_sandbox": "+微步分解+原生function calling+run_python沙盒 (多步分析与出图落地)",
    "v5_memory": "+事实卡记忆压缩(maxlen总结)+trace状态存储溯源 (长对话/跨maxlen依赖)",
    "v6_router": "+路由+意图模板+题面正则兜底 【历史对照版:含对着题型设计的助考机制,仅作归因参考】",
    "v7_general": "去作弊泛化终态: 移除模板/题面正则, 保留问题无关工程(路由/宽表/槽位校验/重试/记忆), 失败诚实化",
    "v8_calculator": "+calculator确定性算术工具(通用,非题库) 【负收益记录: 跨轮失败发生在算术之前, 前置SQL语义错误使计算器无用武之地】",
}


def load(v):
    p = os.path.join(RES, f"{v}_all.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def pct(x, n):
    return 100.0 * x / n if n else 0.0


def main():
    rows = []
    for v in VERSIONS:
        d = load(v)
        if d is None:
            continue
        n = len(d)
        row = {
            "version": v, "n": n,
            "tool_ok": pct(sum(x["tool_ok"] for x in d), n),
            "exec_ok": pct(sum(x["exec_ok"] for x in d), n),
            "answer_ok": pct(sum(x["answer_ok"] for x in d), n),
            "all_turns": pct(sum(x["all_turns_ok"] for x in d), n),
        }
        for suite in ("sql", "pandas", "tool"):
            ds = [x for x in d if x["suite"] == suite]
            row[f"acc_{suite}"] = pct(sum(x["answer_ok"] for x in ds), len(ds)) if ds else None
        rows.append(row)

    print("=" * 100)
    print(f"{'版本':<14}{'N':>4} {'工具OK':>8} {'执行OK':>8} {'最终答对':>8} {'全程答对':>8} "
          f"{'SQL50':>7} {'pandas50':>8} {'tool50':>7}")
    print("-" * 100)
    for r in rows:
        s = lambda k, f="{:.1f}%": (f.format(r[k]) if r.get(k) is not None else "-")
        print(f"{r['version']:<14}{r['n']:>4} {s('tool_ok'):>8} {s('exec_ok'):>8} "
              f"{s('answer_ok'):>8} {s('all_turns'):>8} {s('acc_sql'):>7} {s('acc_pandas'):>8} {s('acc_tool'):>7}")
    print("=" * 100)

    out = os.path.join(RES, "gradient.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("saved ->", out)
    # 分层细节(每版本每level答对率)
    detail = {}
    for v in VERSIONS:
        d = load(v)
        if d is None:
            continue
        agg = {}
        for x in d:
            key = (x["suite"], x["level"])
            a = agg.setdefault(key, [0, 0])
            a[1] += 1
            a[0] += 1 if x["answer_ok"] else 0
        detail[v] = {f"{s}-L{l}": f"{pct(a[0], a[1]):.0f}%({a[0]}/{a[1]})" for (s, l), a in sorted(agg.items())}
    with open(os.path.join(RES, "gradient_by_level.json"), "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=1)
    print("saved -> gradient_by_level.json")


if __name__ == "__main__":
    main()
