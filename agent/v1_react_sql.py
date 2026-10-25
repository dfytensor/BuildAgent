# -*- coding: utf-8 -*-
"""v1 引入ReAct工具循环+sqlite_query工具: 让模型能真正执行SQL拿到真实数据
解决: v0只会凭空编造数字、无法落地查询
遗留: 无库表schema, 列名/表名靠猜 → 大量SQL执行报错
"""
from base_agent import BaseAgent

class AgentV1(BaseAgent):
    name = "v1_react_sql"
    tools = ("sql",)
