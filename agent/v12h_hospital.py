# -*- coding: utf-8 -*-
"""v12h_hospital: 医院域治理代理(基线 + 数据源地图 + 粒度视图提示 + hosp_metric 指标工具)
镜像电商域 v12_views: 口径沉入代码 + 粒度视图 + 数据源地图
"""
import v4_sandbox as v4
from domain_hospital import HOSP_PLANNER_V12, HOSP_TOOLS_V12
from v9_scaffold import AgentV9

v4.PLANNER_SYS = HOSP_PLANNER_V12
v4.TOOLS_SPEC = HOSP_TOOLS_V12


class AgentV12H(AgentV9):
    name = "v12h_hospital"
