# -*- coding: utf-8 -*-
"""v9 脚手架优化(差分诊断驱动, minimax失败归类):
1. 行限20→50(列出全部类不再截断误杀) 2. schema探查直答(零轮次) 3. 房间语义约定(前N=id序)
4. 轮次3→5 5. 评测bug修复(SQL-L1-06题面) — 全部问题无关, 非题型特化
"""
from v7_general import AgentV7


class AgentV9(AgentV7):
    name = "v9_scaffold"
    max_tool_rounds = 5
