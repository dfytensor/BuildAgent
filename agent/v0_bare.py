# -*- coding: utf-8 -*-
"""v0 裸模型基线: 无工具/无schema/无记忆 — 测定模型原生能力边界"""
from base_agent import BaseAgent

class AgentV0(BaseAgent):
    name = "v0_bare"
    tools = ()
    def system_prompt(self):
        return "你是电商数据分析助手, 数据存在SQLite库shop.db中(表: customers, products, orders, order_items)。请直接回答用户的数据问题。"
