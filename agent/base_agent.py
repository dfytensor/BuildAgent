# -*- coding: utf-8 -*-
"""Agent 基类: 文本协议 ReAct 循环。
版本迭代通过 system_prompt() / tools_enabled / memory 策略差异化, 便于对照实验。
"""
import os
import re
import json
import time

from common import chat, tool_sqlite_query, tool_run_python, SandboxSession, TRACE_DIR

TOOL_RE = re.compile(r"TOOL\s*(\{.*\})", re.S)
FINAL_RE = re.compile(r"FINAL[:：]?\s*(.*)", re.S | re.S)


def strip_fence(text):
    return re.sub(r"```[a-zA-Z]*", "", text).strip()


class BaseAgent:
    name = "base"
    tools = ()          # 启用的工具: "sql" / "code"
    max_steps = 6       # 单轮最大工具调用次数
    schema = False      # 是否注入库表说明
    fewshot = False     # 是否注入少样本示例
    heal = False        # 解析失败是否纠偏重试
    memory = False      # 是否启用记忆压缩
    router = False      # 是否启用任务路由

    def __init__(self):
        self.history = []       # 原始对话历史
        self.facts = []         # 压缩事实卡(记忆总结产物)
        self.trace = []         # 全过程追溯
        self.sandbox = SandboxSession() if "code" in self.tools else None
        self.session_id = f"{self.name}_{int(time.time()*1000)}"

    # ---- 提示词 ----
    def system_prompt(self):
        p = "你是电商数据分析助手。"
        if self.schema:
            from common import SCHEMA_TEXT
            p += "\n" + SCHEMA_TEXT
        p += "\n可用工具:"
        if "sql" in self.tools:
            p += '\n[SQL] TOOL {"tool":"sqlite_query","args":{"sql":"SELECT ..."}}'
        if "code" in self.tools:
            p += '\n[代码] TOOL {"tool":"run_python","args":{"code":"pandas代码"}} (变量conn=sqlite连接, plt可用, 图保存到out_dir)'
        p += "\n规则:1.需要查数据才能回答时,先输出一行TOOL;2.得到结果后输出 FINAL+答案;3.FINAL必须含具体数字(别用万/亿),按题目要求保留小数;4.不要编造数据。"
        if self.fewshot:
            p += ('\n示例:\n用户: 深圳的客户有多少位?\nTOOL {"tool":"sqlite_query","args":{"sql":"SELECT COUNT(*) FROM customers WHERE city=\'深圳\'"}}\n'
                  "用户: [结果] {\"columns\":[\"COUNT(*)\"],\"rows\":[[43]]}\nFINAL 深圳的客户共有43位。")
        return p

    def route(self, q):
        """v6: 简单规则路由 — 分析/作图类走代码, 查询类走SQL"""
        if re.search(r"画|图|chart|趋势|分布|对比|增长|占比|top|前\d|最多|最高|最低|平均|率|每月|各", q):
            return "code"
        return "sql"

    # ---- 主循环: 一轮用户输入 -> 最终答案 ----
    def ask(self, user_text):
        steps = []
        msgs = [{"role": "system", "content": self.system_prompt()}]
        msgs += self.build_context()
        user_content = user_text
        if self.router:
            r = self.route(user_text)
            user_content = f"[任务类型:{r}] " + user_text
        msgs.append({"role": "user", "content": user_content})

        answer = None
        err = None
        for i in range(self.max_steps + 1):
            try:
                out = chat(msgs, temperature=0.0, max_tokens=1500 if self.sandbox else 700)
            except Exception as e:
                err = f"(LLM调用失败: {type(e).__name__})"
                break
            out = strip_fence(out)
            m_tool, m_fin = TOOL_RE.search(out), FINAL_RE.search(out)
            if m_tool and (not m_fin or m_tool.start() < m_fin.start()):
                call = self.safe_json(m_tool.group(1))
                result = self.execute(call, steps)
                steps.append({"tool": (call or {}).get("tool"), "args": call, "result": result})
                obs = json.dumps(result, ensure_ascii=False)
                if len(obs) > 1500:
                    obs = obs[:1500] + "...(截断)"
                msgs.append({"role": "assistant", "content": out[:900]})
                msgs.append({"role": "user", "content": f"[工具结果] {obs}\n请继续: 若已够回答则输出FINAL, 否则继续TOOL。"})
            elif m_fin:
                answer = m_fin.group(1).strip() or out
                break
            elif self.heal and i < self.max_steps:
                msgs.append({"role": "assistant", "content": out[:600]})
                msgs.append({"role": "user", "content": "[格式错误] 必须以 TOOL {...} 或 FINAL ... 开头回答, 请重新输出。"})
            else:
                answer = out
                break

        answer = answer or err or "(无答案)"
        self.history.append({"q": user_text, "a": answer})
        self.after_turn(user_text, answer, steps)
        self.trace.append({"turn": len(self.history), "user": user_text, "steps": steps, "answer": answer})
        return answer

    def build_context(self):
        """记忆策略: 默认全量历史; v5起压缩为事实卡"""
        ctx = []
        if self.memory:
            for f in self.facts[-30:]:
                ctx.append({"role": "user", "content": f})
                ctx.append({"role": "assistant", "content": "已记住。"})
        else:
            # 无记忆版: 仅保留最近6轮原始历史(更早的自然失忆, 供跨maxlen用例暴露缺陷)
            for h in self.history[-6:]:
                ctx.append({"role": "user", "content": h["q"]})
                ctx.append({"role": "assistant", "content": h["a"]})
        return ctx

    def after_turn(self, q, a, steps):
        if self.memory:
            # 只有真实工具轮才进事实卡; 填充闲聊不入卡
            if steps:
                ans_part = (a or "").replace("\n", " ")[:200]
                self.facts.append(f"[事实] 问:{q[:60]} 答:{ans_part}")
            # maxlen 控制: 事实卡过长时做二级总结
            total = sum(len(f) for f in self.facts)
            if total > 3600:
                self.facts = [self.facts[0][:200], f"[总结] 更早{len(self.facts)-1}轮要点已压缩"] + self.facts[-10:]

    def execute(self, call, steps):
        if not isinstance(call, dict):
            return {"ok": False, "error": "TOOL不是合法JSON"}
        tool, args = call.get("tool"), call.get("args", {})
        try:
            if tool == "sqlite_query" and "sql" in self.tools:
                return tool_sqlite_query(args, {"session_id": self.session_id, "trace": self.trace})
            if tool == "run_python" and self.sandbox:
                return self.sandbox.run(args, {"session_id": self.session_id, "trace": self.trace})
            if tool == "load_df" and self.sandbox:
                return self.sandbox.load(args.get("sql", ""), {"session_id": self.session_id, "trace": self.trace})
            if tool == "make_chart" and self.sandbox:
                from common import tool_make_chart
                return tool_make_chart(args, {"session_id": self.session_id, "trace": self.trace})
            if tool == "calculator":
                from common import tool_calculator
                return tool_calculator(args, {"session_id": self.session_id, "trace": self.trace})
            if tool == "query_metric":
                from query_metric import tool_query_metric
                return tool_query_metric(args, {"session_id": self.session_id, "trace": self.trace})
            from common import EXTRA_TOOLS
            if tool in EXTRA_TOOLS:
                return EXTRA_TOOLS[tool](args, {"session_id": self.session_id, "trace": self.trace})
            return {"ok": False, "error": f"工具不可用: {tool}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def safe_json(s):
        s = s.strip()
        try:
            return json.loads(s)
        except Exception:
            try:
                return json.loads(s[:s.rindex("}") + 1])
            except Exception:
                return None

    def save_trace(self, case_id):
        path = os.path.join(TRACE_DIR, f"{self.name}_{case_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"agent": self.name, "case": case_id, "trace": self.trace}, f, ensure_ascii=False, indent=1)
        return path

    def cleanup(self):
        if self.sandbox:
            self.sandbox.cleanup()
