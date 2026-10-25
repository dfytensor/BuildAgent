# -*- coding: utf-8 -*-
"""最终验证: 1B(cpm5-1b) 端到端多轮商业数据分析 — v7_general 去作弊泛化版
场景: 运营分析师的一天 — 总览/趋势/出图/品类/区域对比/跨轮引用
产出: 控制台对话记录 + 图表文件 + 溯源trace
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent"))
from v7_general import AgentV7

TURNS = [
    ("轮1 总览", "2024年全年完成的销售额是多少? 保留2位"),
    ("轮2 趋势", "2024年哪个月的销售额最高? 是多少?"),
    ("轮3 出图", "画2024年每月销售额柱状图, 保存为 chart_demo_01.png"),
    ("轮4 品类", "2024年各类目的销售额分别是多少? (已完成订单)"),
    ("轮5 区域对比", "华东和华南区域2024年的销售额对比一下, 差多少?"),
    ("轮6 压力填充", "这是条无关消息, 用于测试长对话稳定性。" * 3),
    ("轮7 跨轮引用", "回到轮2, 那个最高月份的销售额占全年销售额的百分之几? 保留2位"),
]


def main():
    ag = AgentV7()
    print("=" * 72)
    print("cpm5-1b 智能数据分析Agent — 端到端验证(v7_general 去作弊泛化版, 无微调1B)")
    print("=" * 72)
    total_t0 = time.time()
    for tag, q in TURNS:
        t0 = time.time()
        a = ag.ask(q)
        steps_desc = "; ".join(
            f"{s['tool']}({'OK' if s['result'].get('ok') else 'FAIL'})" for s in ag.trace[-1]["steps"])
        print(f"\n[{tag}] ({time.time()-t0:.1f}s) 用户: {q}")
        print(f"  Agent: {a[:220]}")
        print(f"  [工具] {steps_desc or '无'}")
    ag.save_trace("final_demo")
    ag.cleanup()
    dt = time.time() - total_t0
    charts = [f for f in os.listdir("artifacts") if f.startswith("chart_demo")]
    trace_file = os.path.join("artifacts", "trace", "v7_general_final_demo.json")
    print("\n" + "=" * 72)
    print(f"完成: {len(TURNS)}轮对话, 总耗时 {dt:.0f}s")
    print(f"图表产物: {charts}")
    print(f"溯源trace: {trace_file} ({os.path.getsize(trace_file)} bytes)" if os.path.exists(trace_file) else "trace缺失!")
    print(f"事实卡(记忆压缩): {len(ag.facts)}条")


if __name__ == "__main__":
    main()
