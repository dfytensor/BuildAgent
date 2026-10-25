# -*- coding: utf-8 -*-
"""v3 自愈机制: v2证据显示schema让SQL内容正确但TOOL协议崩塌(模型直接写SQL当答案)
引入: few-shot格式锚定(对话示例) + 解析失败纠偏重试(格式错误喂回去重答)
解决: 工具调用协议成功率(格式漂移/自导自演伪造结果)
遗留: SQL做不了的多步分析与出图仍无解
"""
from base_agent import BaseAgent


class AgentV3(BaseAgent):
    name = "v3_selfheal"
    tools = ("sql",)
    schema = True
    fewshot = True
    heal = True
    max_steps = 4  # 纯SQL版不需要6步, 控制纠偏循环成本
