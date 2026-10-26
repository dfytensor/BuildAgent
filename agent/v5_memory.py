# -*- coding: utf-8 -*-
"""v5 记忆压缩(maxlen总结) + 状态存储(溯源): v4证据显示多轮依赖/跨maxlen是主要缺陷
引入: 事实卡记忆(带数字/工具结果的轮次压缩为短事实, 填充闲聊不入卡, 超限二级总结)
      + 规划器/回答器注入事实卡 + 每会话状态快照落盘(artifacts/trace可审计)
解决: 长对话上下文溢出、跨maxlen依赖丢失、过程可溯源
"""
import json
import os

from base_agent import BaseAgent
from common import summarize_result
from v4_sandbox import AgentV4


class AgentV5(AgentV4):
    name = "v5_memory"
    memory = True  # 启用事实卡

    def _facts_text(self):
        if not self.facts:
            return ""
        return "\n".join(self.facts[-24:])

    def _planner_msgs(self, user_text, observations):
        msgs = super()._planner_msgs(user_text, observations)
        f = self._facts_text()
        if f:
            msgs.insert(1, {"role": "user", "content": f"[此前会话事实卡]\n{f}\n[事实卡结束]"})
            msgs.insert(2, {"role": "assistant", "content": "已读取事实卡。"})
        return msgs

    def _answer_msgs(self, user_text, observations):
        from v4_sandbox import ANSWER_SYS
        content = f"用户问题: {user_text}"
        ctx_rich = os.environ.get("ANSWER_CTX") == "1"
        for i, (call, res) in enumerate(observations):
            if ctx_rich:
                args = (call or {}).get("args", {}) if isinstance(call, dict) else {}
                brief = args.get("sql") or args.get("expression") or args.get("metric") or ""
                if brief:
                    content += f"\n[工具{i+1}调用] {str(brief)[:200]}"
            content += f"\n[工具{i+1}结果] {summarize_result(res)}"
        f = self._facts_text()
        if f:
            content = f"[此前会话事实卡]\n{f}\n[事实卡结束]\n" + content
        return [{"role": "system", "content": ANSWER_SYS},
                {"role": "user", "content": content[:6000]}]

    def save_trace(self, case_id):
        import json as _json
        import os
        from common import TRACE_DIR
        path = os.path.join(TRACE_DIR, f"{self.name}_{case_id}.json")
        with open(path, "w", encoding="utf-8") as fp:
            _json.dump({"agent": self.name, "case": case_id, "trace": self.trace,
                        "state": {"facts": self.facts, "history": self.history}},
                       fp, ensure_ascii=False, indent=1)
        return path
