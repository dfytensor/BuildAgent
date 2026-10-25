# -*- coding: utf-8 -*-
"""v10 语义层/指标注册表: 业务口径做成确定性工具(模型填槽), 消除口径类/粒度类错误
继承 v9 全部脚手架(行限50/schema直答/语义约定/轮次5/子进程隔离/限流合规)
"""
from v9_scaffold import AgentV9


class AgentV10(AgentV9):
    name = "v10_metric"
