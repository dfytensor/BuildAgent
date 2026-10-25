# -*- coding: utf-8 -*-
"""v2 注入库表schema: 解决v1列名/表名/枚举值幻觉导致的SQL报错
遗留: SQL表达不了多步分析(留存/环比/出图) → 需要代码工具
"""
from base_agent import BaseAgent

class AgentV2(BaseAgent):
    name = "v2_schema"
    tools = ("sql",)
    schema = True
