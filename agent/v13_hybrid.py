# -*- coding: utf-8 -*-
"""v13 混合策略: 复杂SQL -> 简单SQL取数 + pandas 处理
适用: 多表JOIN/子查询/窗口/多层聚合等 4B 易错的复杂 SQL
"""
from v9_scaffold import AgentV9


class AgentV13(AgentV9):
    name = "v13_hybrid"

    def planner_hint(self, user_text):
        base = super().planner_hint(user_text)
        tip = ("\n[混合策略] 需要多表JOIN/子查询/窗口函数/多层聚合时, 不要写复杂SQL: "
               "先写简单SELECT取出所需列(可带基本WHERE/LIMIT), 再用 run_python 的 pandas 做 "
               "merge/groupby/sort/计算; 简单单表查询仍直接用 sqlite_query。"
               "pandas 里可用 conn 连接数据库读取, 最后 print 结果。")
        return base + tip
