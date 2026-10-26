# -*- coding: utf-8 -*-
"""v13d 强制 PANDAS 诊断臂: 所有题都走 load_df + run_python, 验证 4B 能否用 pandas 替代复杂 SQL"""
from v13c_gated import AgentV13C
from v4_sandbox import TOOLS_SPEC
from v9_scaffold import AgentV9


class AgentV13D(AgentV13C):
    name = "v13d_forced"

    def ask(self, user_text):
        self._path = "PANDAS"
        self.tool_spec = [t for t in TOOLS_SPEC
                          if t["function"]["name"] in ("load_df", "run_python", "calculator")]
        return AgentV9.ask(self, user_text)
