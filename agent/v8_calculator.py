# -*- coding: utf-8 -*-
"""v8 确定性算术执行器: v7证据显示跨轮算术是T4/T6归零的直接原因
   (数值能召回, 但1B心算不可靠)
引入: calculator工具(模型从事实卡抄数值组装表达式, 代码AST白名单求值)
      + 计算必须走calculator的强规则
泛化性: 计算器对任意数值/任意算式成立, 不含任何题库知识
"""
from v7_general import AgentV7


class AgentV8(AgentV7):
    name = "v8_calculator"
