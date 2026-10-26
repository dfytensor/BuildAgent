# -*- coding: utf-8 -*-
"""v13c 硬门禁: PANDAS 路径下工具表只保留 load_df/run_python/calculator/query_metric"""
from v13b_hybrid2 import AgentV13B
from v4_sandbox import TOOLS_SPEC
from v9_scaffold import AgentV9


class AgentV13C(AgentV13B):
    name = "v13c_gated"

    def ask(self, user_text):
        self._path = self._choose_path(user_text)
        if self._path == "PANDAS":
            self.tool_spec = [t for t in TOOLS_SPEC
                              if t["function"]["name"] in ("load_df", "run_python", "calculator", "query_metric")]
        else:
            self.tool_spec = TOOLS_SPEC
        return AgentV9.ask(self, user_text)
