# -*- coding: utf-8 -*-
"""v6 任务路由(格物致知终态): 确定性代码路由替代模型自判断
v4/v5证据: 1B对"要不要调工具/用哪个工具"的判断不可靠
引入: 关键词路由(数据→规划器+强制提醒; 闲聊→直答) + 图表确定性管线(槽位填充+正则兜底, 保证出图)
解决: 工具调用率、图表产出、端到端稳定性, 让1B完成简单数据分析任务
"""
import re
import json

from common import chat, client, MODEL_ID, tool_make_chart
from v5_memory import AgentV5
from v4_sandbox import PLANNER_SYS

DATA_RE = re.compile(
    r"多少|几|哪些|哪一|排名|排行|画|图|chart|率|额|最高|最低|平均|总共|合计|"
    r"前\d|top|Top|TOP|统计|占比|增长|分析|订单|客户|商品|销售|消费|金额|vip|VP|查")
CHART_RE = re.compile(r"画|图|chart|饼|折线|柱状|直方")

CHART_TOOL_SPEC = [{
    "type": "function", "function": {
        "name": "make_chart",
        "description": "画图。type: line折线/bar柱状/pie饼/hist直方; dim: month/year/day/region/category/status/channel/city/vip_level(hist用price); metric: count/amount/quantity/price; filters可选{\"year\":2024,\"status\":\"completed\",\"category\":\"数码\"}等; filename如chart_01.png",
        "parameters": {"type": "object", "properties": {
            "type": {"type": "string"}, "dim": {"type": "string"},
            "metric": {"type": "string"}, "filters": {"type": "object"},
            "filename": {"type": "string"}},
            "required": ["type", "dim", "metric"]}}}]

TYPE_RE = [("折线", "line"), ("柱状", "bar"), ("条形", "bar"), ("饼", "pie"), ("直方", "hist"), ("分布", "hist")]
DIM_RE = [("每月", "month"), ("各月", "month"), ("按月", "month"), ("各区域", "region"), ("各类目", "category"),
          ("各渠道", "channel"), ("状态", "status"), ("vip", "vip_level"), ("价格分布", "price"), ("城市", "city")]
METRIC_RE = [("销售额", "amount"), ("金额", "amount"), ("消费", "amount"), ("销售", "amount"),
             ("订单数", "count"), ("客户数", "count"), ("数量", "count"), ("件数", "quantity")]


def regex_slots(q):
    slots = {"type": "bar", "dim": "month", "metric": "count", "filters": {}, "filename": ""}
    for kw, v in TYPE_RE:
        if kw in q:
            slots["type"] = v
            break
    for kw, v in DIM_RE:
        if kw in q:
            slots["dim"] = v
            break
    for kw, v in METRIC_RE:
        if kw in q:
            slots["metric"] = v
            break
    if slots["dim"] == "price":
        slots["type"] = "hist"
    m = re.search(r"(20\d{2})", q)
    if m:
        slots["filters"]["year"] = int(m.group(1))
    if "已完成" in q or "完成订单" in q:
        slots["filters"]["status"] = "completed"
    fm = re.search(r"chart_\d+\.png", q)
    if fm:
        slots["filename"] = fm.group(0)
    return slots


class AgentV6(AgentV5):
    name = "v6_router"

    def is_data_q(self, q):
        return bool(DATA_RE.search(q))

    def force_tool(self, user_text):
        return True

    def planner_hint(self, user_text):
        if CHART_RE.search(user_text):
            return "\n[强规则] 图表类问题必须调用 make_chart 工具(填type/dim/metric/filters/filename即可), 不要用SQL或run_python画图。"
        return ""

    def empty_retry(self, result):
        return True

    REFUSE_RE = re.compile(r"无法访问|无法获取|无法提供|无法直接|无法查看|无法看到")

    def _planner_msgs(self, user_text, observations):
        msgs = super()._planner_msgs(user_text, observations)
        # 历史卫生: 拒绝性回答不进入规划器上下文(防拒绝话术级联传染)
        return [m for m in msgs
                if not (m.get("role") == "assistant" and self.REFUSE_RE.search(m.get("content", "")))]

    # ---- 图表确定性管线: 模型填槽 -> 正则兜底 -> 必出图 ----
    def chart_pipeline(self, q):
        slots = None
        micro = [{"role": "system", "content": "你是图表参数填充器, 只输出对make_chart工具的一次调用, 参数从用户问题中提取; 提取不到的用默认值。"},
                 {"role": "user", "content": q}]
        for attempt in range(2):
            try:
                r = client().chat.completions.create(
                    model=MODEL_ID, messages=micro, temperature=0.0,
                    max_tokens=250, tools=CHART_TOOL_SPEC)
                msg = r.choices[0].message
                if msg.tool_calls and msg.tool_calls[0].function.name == "make_chart":
                    s = json.loads(msg.tool_calls[0].function.arguments or "{}")
                    if isinstance(s, dict) and s.get("type"):
                        slots = s
                        break
            except Exception:
                pass
            if attempt == 0:
                micro[-1]["content"] = q + "\n(必须调用make_chart工具)"
        if not isinstance(slots, dict):
            slots = regex_slots(q)
        # 逐槽校验: 非法值回退到正则提取
        fb = regex_slots(q)
        for k, valid in (("type", {"line", "bar", "pie", "hist"}),
                         ("dim", {"month", "year", "day", "region", "category", "status",
                                  "channel", "city", "vip_level", "price", "quantity", "amount"}),
                         ("metric", {"count", "amount", "quantity", "price"})):
            v = slots.get(k)
            if not isinstance(v, str) or v.lower() not in valid:
                slots[k] = fb[k]
        if not isinstance(slots.get("filters"), dict):
            slots["filters"] = {}
        slots["filters"] = {k: v for k, v in slots["filters"].items() if k in ("year", "month", "status", "channel", "region", "city", "category", "vip_level")}
        slots.setdefault("filename", "")
        if CHART_RE.search(q):
            fm = re.search(r"chart_\d+\.png", q)
            if fm:
                slots["filename"] = fm.group(0)
        res = tool_make_chart(slots, {"session_id": self.session_id, "trace": self.trace})
        self.trace[-1]["steps"].append({"tool": "make_chart", "args": slots, "result": res})
        if res.get("ok"):
            fn = slots.get("filename") or "chart.png"
            return f"FINAL 图表已生成并保存为 {fn}。(类型:{slots.get('type')}, 维度:{slots.get('dim')}, 指标:{slots.get('metric')})"
        return f"FINAL 查询失败: 图表生成未成功({str(res.get('error'))[:80]})"

    # ---- 常见意图模板库: 参数化SQL + 代码算差值/占比 (高频意图模板优先, 模型处理长尾) ----
    def template_fallback(self, q):
        import sqlite3
        from common import DB_PATH
        year_m = re.search(r"(20\d{2})", q)
        year = year_m.group(1) if year_m else "2024"
        try:
            conn = sqlite3.connect(DB_PATH)
            total = conn.execute(
                "SELECT ROUND(SUM(amount),2) FROM v_sales WHERE status='completed' AND year=?",
                (year,)).fetchone()[0]
            if re.search(r"哪个月.{0,8}最高|最高.{0,8}月份", q) and re.search(r"销售|额|消费", q):
                rows = conn.execute(
                    "SELECT month, ROUND(SUM(amount),2) FROM v_sales WHERE status='completed' AND year=? GROUP BY month ORDER BY 2 DESC LIMIT 1",
                    (year,)).fetchall()
                conn.close()
                if rows and total:
                    pct = round(rows[0][1] * 100.0 / total, 2)
                    if re.search(r"百分比|占比|百分之|占全年", q):
                        return (f"FINAL {year}年销售额最高的月份是 {rows[0][0]}, 当月销售额 {rows[0][1]} 元, "
                                f"占全年总销售额({total}元)的 {pct}%。")
                    return f"FINAL {year}年销售额最高的月份是 {rows[0][0]}, 当月销售额 {rows[0][1]} 元。"
            if re.search(r"各类目|每个类目|类目.{0,4}销售", q):
                rows = conn.execute(
                    "SELECT category, ROUND(SUM(amount),2) FROM v_sales WHERE status='completed' AND year=? GROUP BY category ORDER BY 2 DESC",
                    (year,)).fetchall()
                conn.close()
                if rows:
                    body = "; ".join(f"{r[0]} {r[1]}元" for r in rows)
                    return f"FINAL {year}年各类目销售额(已完成订单, 从高到低): {body}。"
            regions = [r for r in ("华东", "华北", "华南", "西南", "东北") if r in q]
            if len(regions) >= 2 and re.search(r"对比|比较|差|哪个高|占比", q):
                vals = {}
                for rg in regions:
                    row = conn.execute(
                        "SELECT ROUND(SUM(amount),2) FROM v_sales WHERE status='completed' AND year=? AND region=?",
                        (year, rg)).fetchone()
                    vals[rg] = row[0] or 0
                conn.close()
                pairs = sorted(vals.items(), key=lambda kv: -kv[1])
                diff = round(pairs[0][1] - pairs[-1][1], 2)
                body = "; ".join(f"{k} {v}元" for k, v in pairs)
                return f"FINAL {year}年各区域销售额对比(已完成订单): {body}; 最高与最低相差 {diff} 元。"
            conn.close()
            if total is not None and re.search(r"全年|总.{0,3}销售|销售.{0,4}总额|销售额是多少|总销售额", q) and not re.search(r"哪个|哪月|哪个月|对比|类目|区域", q):
                return f"FINAL {year}年全年已完成订单总销售额为 {total} 元。"
        except Exception:
            pass
        return None

    def ask(self, user_text):
        if CHART_RE.search(user_text):
            self.trace.append({"turn": len(self.history) + 1, "user": user_text, "steps": [], "answer": "", "route": "chart"})
            ans = self.chart_pipeline(user_text)
            self.history.append({"q": user_text, "a": ans})
            self.after_turn(user_text, ans, self.trace[-1]["steps"])
            self.trace[-1]["answer"] = ans
            return ans
        if not self.is_data_q(user_text):
            msgs = [{"role": "system", "content": "你是简洁的助手, 用一句话回答。"}]
            for h in self.history[-4:]:
                msgs.append({"role": "user", "content": h["q"][:150]})
                msgs.append({"role": "assistant", "content": h["a"][:100]})
            msgs.append({"role": "user", "content": user_text})
            try:
                answer = chat(msgs, temperature=0.0, max_tokens=150)
            except Exception:
                answer = "(回答失败)"
            self.history.append({"q": user_text, "a": answer})
            self.after_turn(user_text, answer, [])
            self.trace.append({"turn": len(self.history), "user": user_text,
                               "steps": [], "answer": answer, "route": "chat"})
            return answer
        # 高频意图模板优先(确定性), 未命中再走模型规划(处理长尾问法)
        tans = self.template_fallback(user_text)
        if tans:
            self.trace.append({"turn": len(self.history) + 1, "user": user_text,
                               "steps": [], "answer": tans, "route": "template"})
            self.history.append({"q": user_text, "a": tans})
            self.after_turn(user_text, tans, [])
            return tans
        ans = super().ask(user_text)
        self.trace[-1]["route"] = "data"
        # 兜底: 模型路径没有产出任何成功的工具结果时, 意图模板补位
        steps = self.trace[-1].get("steps", [])
        if not any(s["result"].get("ok") for s in steps):
            tans = self.template_fallback(user_text)
            if tans:
                self.trace[-1]["route"] = "template"
                self.trace[-1]["answer"] = tans
                self.history[-1]["a"] = tans
                self.after_turn(user_text, tans, self.trace[-1]["steps"])
                ans = tans
        return ans
