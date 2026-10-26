# -*- coding: utf-8 -*-
"""v13b 结构性混合路径: 路径选择器(SQL/PANDAS) + load_df(SQL->DataFrame) + run_python
与 v13 的区别: 不是"提示模型换路径", 而是先用微任务判定路径, PANDAS 路径下强制 load_df 取数
"""
from common import chat
from v9_scaffold import AgentV9


class AgentV13B(AgentV9):
    name = "v13b_hybrid2"

    def __init__(self):
        super().__init__()
        self._path = "SQL"

    def _choose_path(self, q):
        msgs = [
            {"role": "system", "content": "你是任务路由器。只回答一个词: SQL 或 PANDAS。"},
            {"role": "user", "content": (
                "问题: " + q[:300] +
                "\n规则: 单表过滤/计数/排序/简单聚合 -> SQL; "
                "需要多表JOIN/子查询/窗口函数/多步聚合/占比/复杂计算 -> PANDAS。\n只回答一个词。")},
        ]
        try:
            out = (chat(msgs, temperature=0.0, max_tokens=8) or "").strip().upper()
        except Exception:
            return "SQL"
        if "PANDAS" in out:
            return "PANDAS"
        if "SQL" in out:
            return "SQL"
        return "SQL"

    def ask(self, user_text):
        self._path = self._choose_path(user_text)
        return super().ask(user_text)

    def planner_hint(self, user_text):
        base = super().planner_hint(user_text)
        if self._path == "PANDAS":
            return base + (
                "\n[路径] 本题判定为复杂分析: 必须先用 load_df 取数(可多次), "
                "再用 run_python 的 pandas 做 merge/groupby/sort/计算; 禁止写复杂SQL。")
        return base
