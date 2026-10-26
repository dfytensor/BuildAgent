# -*- coding: utf-8 -*-
"""v9h_baseline: 医院域基线代理(无数据源地图/无指标工具/无粒度视图提示)
镜像电商域 v9: schema + 方言 + 口径 + 计算规则 + 语义约定, 工具只有 sqlite/run_python/calculator
"""
import v4_sandbox as v4
from domain_hospital import HOSP_PLANNER_BASE, HOSP_TOOLS_BASE
from v9_scaffold import AgentV9

v4.PLANNER_SYS = HOSP_PLANNER_BASE
v4.TOOLS_SPEC = HOSP_TOOLS_BASE


class AgentV9H(AgentV9):
    name = "v9h_baseline"
