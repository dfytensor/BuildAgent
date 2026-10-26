# -*- coding: utf-8 -*-
"""v12 数据治理: v_orders / v_customers / v_product_sales 语义视图 + 数据源地图
目标: 把"行粒度重复 / 空明细NULL / 款件混淆"从提示词约束升级为表结构约束
"""
from v9_scaffold import AgentV9


class AgentV12(AgentV9):
    name = "v12_views"
