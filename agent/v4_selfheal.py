# -*- coding: utf-8 -*-
"""v4 自愈机制(few-shot格式锚定+解析失败纠偏重试): 解决1B输出格式漂移、可执行率低
解决: TOOL/FINAL解析失败率大幅下降, 工具调用格式稳定
遗留: 多轮长对话撑爆2048上下文, 跨maxlen依赖丢失; 过程不可溯源
"""
from base_agent import BaseAgent

class AgentV4(BaseAgent):
    name = "v4_selfheal"
    tools = ("sql", "code")
    schema = True
    fewshot = True
    heal = True
