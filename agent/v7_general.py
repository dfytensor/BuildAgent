# -*- coding: utf-8 -*-
"""v7 泛化版(去作弊终态): v6证据显示模板库/题面正则兜底对着题型设计, 无泛化性
移除: 意图模板库(总销售额/月度Top等直答), 从题面正则提取图表参数(regex_slots)
保留(问题无关的通用工程): 关键词路由 / 宽表视图 / make_chart受约束接口 /
      槽位白名单校验 / 校验失败带错重试 / 报错与空结果重试 / 强制工具提醒 /
      历史卫生(拒绝话术过滤) / 事实卡记忆 / 全程trace溯源
失败语义: 模型解析不出就明确报告失败并给出建议, 不给幻觉答案
"""
import os
import re
import json

from common import chat, client, MODEL_ID, tool_make_chart
from v5_memory import AgentV5
from v4_sandbox import PLANNER_SYS
from v6_router import DATA_RE, CHART_RE, CHART_TOOL_SPEC

VALID_TYPES = {"line", "bar", "pie", "hist"}
VALID_DIMS = {"month", "year", "day", "region", "category", "status",
              "channel", "city", "vip_level", "price", "quantity", "amount"}
VALID_METRICS = {"count", "amount", "quantity", "price"}
VALID_FILTER_KEYS = {"year", "month", "day", "status", "channel", "region",
                     "city", "category", "vip_level"}

# 通用词表归一化(同义词, 与具体题目无关)
SYNONYMS = {
    "line_chart": "line", "bar_chart": "bar", "pie_chart": "pie", "histogram": "hist",
    "curve": "line", "column": "bar", "barchart": "bar", "linechart": "line",
    "months": "month", "years": "year", "days": "day", "regions": "region",
    "category_name": "category", "categories": "category", "product_category": "category",
    "channels": "channel", "cities": "city", "vip": "vip_level", "date": "month",
    "sales": "amount", "sale": "amount", "revenue": "amount", "sales_amount": "amount",
    "orders": "count", "order": "count", "order_count": "count", "num": "count",
    "quantity_sold": "quantity", "qty": "quantity", "avg_price": "price", "total": "amount",
}


def _norm_token(v, valid):
    """复合值拆分 + 同义词归一; 返回合法值或 None"""
    if not isinstance(v, str):
        return None
    for tok in re.split(r"[/,、;| ]+", v.strip().lower()):
        tok = SYNONYMS.get(tok, tok)
        if tok in valid:
            return tok
    return None


def coerce_slots(s):
    """宽容归一: 字符串filters转对象, 数值字符串转int, 复合/同义词值归一"""
    if not isinstance(s, dict):
        return s
    f = s.get("filters")
    if isinstance(f, str):
        try:
            import ast
            f2 = ast.literal_eval(f)
            f = f2 if isinstance(f2, dict) else {}
        except Exception:
            f = {}
        s["filters"] = f
    if isinstance(s.get("filters"), dict):
        for k in list(s["filters"].keys()):
            kk = SYNONYMS.get(str(k).lower(), str(k).lower())
            v = s["filters"].pop(k)
            if isinstance(v, str) and v.isdigit():
                v = int(v)
            s["filters"][kk] = v
        s["filters"] = {k: v for k, v in s["filters"].items() if k in VALID_FILTER_KEYS}
    for k, valid in (("type", VALID_TYPES), ("dim", VALID_DIMS), ("metric", VALID_METRICS)):
        t = _norm_token(s.get(k), valid)
        if t:
            s[k] = t
    return s


def validate_slots(s):
    """槽位白名单校验(问题无关), 返回 (ok, err)"""
    if not isinstance(s, dict):
        return False, "参数不是对象"
    t = str(s.get("type", "")).lower()
    d = str(s.get("dim", "")).lower()
    m = str(s.get("metric", "")).lower()
    if t not in VALID_TYPES:
        return False, f"type的值无效(得到'{s.get('type')}'), 只填一个英文小写词, 参考工具描述"
    if d not in VALID_DIMS:
        return False, f"dim的值无效(得到'{s.get('dim')}'), 只填一个英文小写词, 参考工具描述"
    if m not in VALID_METRICS:
        return False, f"metric的值无效(得到'{s.get('metric')}'), 只填一个英文小写词, 参考工具描述"
    f = s.get("filters") or {}
    if not isinstance(f, dict):
        return False, "filters须为对象"
    for k in f:
        if k not in VALID_FILTER_KEYS:
            return False, f"filters的键须为{sorted(VALID_FILTER_KEYS)}, 得到 {k}"
    return True, ""


SLOT_SYS = ("你是图表参数填充器。如需思考请保持极简(3行内), 最终必须输出对make_chart工具的一次调用, "
            "参数从用户问题中提取; 提取不到的用合理默认值(type=bar, dim=month, metric=count)。"
            "type/dim/metric各只填一个英文小写词, filters是对象如{\"year\": 2024}。")


class AgentV7(AgentV5):
    name = "v7_general"

    def is_data_q(self, q):
        return bool(DATA_RE.search(q))

    def force_tool(self, user_text):
        return True

    def empty_retry(self, result):
        return True

    def planner_hint(self, user_text):
        if CHART_RE.search(user_text):
            return "\n[强规则] 图表类问题必须调用 make_chart 工具(填type/dim/metric/filters/filename即可)。"
        return ""

    REFUSE_RE = re.compile(r"无法访问|无法获取|无法提供|无法直接|无法查看|无法看到|查询失败|回答失败|\(无答案\)")

    def __init__(self):
        super().__init__()
        self.data_history = []  # 仅数据/图表轮, 供规划器携带(闲聊轮不干扰规划)

    def _remember_data(self, q, a):
        self.data_history.append({"q": q[:120], "a": a[:120]})

    def _planner_msgs(self, user_text, observations):
        msgs = [{"role": "system", "content": PLANNER_SYS + self.planner_hint(user_text)}]
        for h in self.data_history[-3:]:
            if self.REFUSE_RE.search(h["a"]):
                continue  # 历史卫生: 失败/拒绝轮不入规划器上下文
            msgs.append({"role": "user", "content": h["q"]})
            msgs.append({"role": "assistant", "content": h["a"]})
        content = user_text
        for i, (call, res) in enumerate(observations):
            content += f"\n[第{i+1}次工具调用] {json.dumps(call, ensure_ascii=False)[:200]}\n[结果] {json.dumps(res, ensure_ascii=False)[:600]}"
        if observations:
            content += "\n若以上数据已足够回答请直接文字回答; 还需不同数据则调用工具。不要重复上一次相同的调用。"
        msgs.append({"role": "user", "content": content[:2000]})
        return msgs

    # ---- 图表: 模型填槽 + 白名单校验 + 带错重试(无题面正则兜底) ----
    def chart_pipeline(self, q):
        micro = [{"role": "system", "content": SLOT_SYS},
                 {"role": "user", "content": q}]
        slots, last_err = None, ""
        for attempt in range(3):
            try:
                r = client().chat.completions.create(
                    model=MODEL_ID, messages=micro, temperature=0.0,
                    max_tokens=1200, tools=CHART_TOOL_SPEC)
                msg = r.choices[0].message
                msg = r.choices[0].message
                call = None
                if msg.tool_calls and msg.tool_calls[0].function.name == "make_chart":
                    try:
                        call = json.loads(msg.tool_calls[0].function.arguments or "{}")
                    except Exception:
                        call = None
                elif msg.content and "make_chart" in msg.content:
                    # 服务端偶发把工具调用以文本形式返回, 宽容解析
                    m2 = re.search(r'"arguments"\s*:\s*(\{.*\})', msg.content, re.S)
                    if m2:
                        try:
                            call = json.loads(m2.group(1))
                        except Exception:
                            call = None
                if call is not None:
                    s = coerce_slots(call)
                    ok, err = validate_slots(s)
                    if ok:
                        slots = s
                        break
                    last_err = err
                    micro = micro[:2] + [
                        {"role": "assistant", "content": f"make_chart({_dumps(s)})"},
                        {"role": "user", "content": f"[参数错误] {err}\n请修正后重新调用make_chart。"}]
                else:
                    last_err = "未调用make_chart工具"
                    micro = micro[:2] + [
                        {"role": "user", "content": "必须调用make_chart工具, 重新输出。"}]
            except Exception as e:
                last_err = f"{type(e).__name__}"
        if slots is None:
            # 诚实失败: 不编造图表
            return ("FINAL 查询失败: 无法从问题中解析出有效的图表参数"
                    f"({last_err[:60]})。请明确说明: 图表类型(折线/柱状/饼/直方)、"
                    "统计维度(如月份/类目/区域)与指标(如销售额/订单数)。")
        # 文件名属于I/O指令遵循(问题显式给出时采纳), 不含答案信息
        fm = re.search(r"chart_\w+\.png", q)
        if fm:
            slots["filename"] = fm.group(0)
        slots.setdefault("filters", {})
        res = tool_make_chart(slots, {"session_id": self.session_id, "trace": self.trace})
        self.trace[-1]["steps"].append({"tool": "make_chart", "args": slots, "result": res})
        if res.get("ok"):
            fn = slots.get("filename") or (res.get("saved") and os.path.basename(res["saved"])) or "chart.png"
            return (f"FINAL 图表已生成并保存为 {fn}。"
                    f"(类型:{slots.get('type')}, 维度:{slots.get('dim')}, 指标:{slots.get('metric')})")
        return f"FINAL 查询失败: 图表生成未成功({str(res.get('error'))[:80]})"

    def ask(self, user_text):
        if CHART_RE.search(user_text):
            self.trace.append({"turn": len(self.history) + 1, "user": user_text,
                               "steps": [], "answer": "", "route": "chart"})
            ans = self.chart_pipeline(user_text)
            self.history.append({"q": user_text, "a": ans})
            self.after_turn(user_text, ans, self.trace[-1]["steps"])
            self._remember_data(user_text, ans)
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
        ans = super().ask(user_text)
        self.trace[-1]["route"] = "data"
        self._remember_data(user_text, ans)
        return ans


def _dumps(o):
    try:
        return json.dumps(o, ensure_ascii=False)[:200]
    except Exception:
        return str(o)[:200]
