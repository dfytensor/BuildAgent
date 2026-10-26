# -*- coding: utf-8 -*-
"""v12c calculator 结果直通: 回答器上下文显式标注"已验证计算结果"
修两类 4B 失败: ①长数字转录错位(T4-07: 12548.96 抄成 1254.91) ②忽略计算器结果只答单价(T3-05)
原则: 计算已由 calculator 代码完成(判断权下沉), 回答器只负责引用措辞
"""
from v9_scaffold import AgentV9


class AgentV12C(AgentV9):
    name = "v12c_calcpy"

    def _answer_msgs(self, user_text, observations):
        msgs = super()._answer_msgs(user_text, observations)
        calcs = []
        for call, res in observations:
            if (isinstance(res, dict) and res.get("ok")
                    and "value" in res and "expression" in res):
                calcs.append(f"{res['expression']} = {res['value']}")
        if calcs:
            msgs[-1]["content"] += (
                "\n[已验证计算结果(由calculator代码计算, 引用时逐位照抄, 可直接作为最终答案)]: "
                + "; ".join(calcs[-3:]))
        return msgs
