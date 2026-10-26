# -*- coding: utf-8 -*-
"""v4 微步分解 + 代码沙盒: v3证据显示1B无法在一条回复里同时遵守"协议+schema+格式"多约束
引入: 两段式微任务分解(规划器只输出一行TOOL/NO_TOOL; 回答器只依据结果写FINAL)
      + run_python有状态沙盒(pandas/matplotlib, 代码报错回传规划器自修复)
解决: 协议成功率(微任务对1B友好), 复杂分析与出图落地
遗留: 长对话历史压缩、跨maxlen依赖、过程溯源
"""
import os
import re
import json

from base_agent import BaseAgent, strip_fence
from common import chat, client, MODEL_ID

PLANNER_SYS = """你是电商数据分析规划器, 已连接本电商数据库(工具可直接查询全部业务数据, 不要在表名前加任何库名前缀)。
业务规则:
- 销售额=SUM(quantity*unit_price*(1-discount)), 只统计已完成订单须过滤 orders.status='completed'
- status枚举: completed已完成/cancelled已取消/pending待处理; channel: app/web/mini_program小程序
- region: 华东/华北/华南/西南/东北; 类目: 数码/家电/服饰/食品/美妆/家居
语义约定(重要):
- "前N个/最早N个" = 按主键id升序的前N个(如前5个订单=ORDER BY id LIMIT 5), 不是Top-N排行
- "列出/列出全部"类问题 = 返回完整列表(结果最多50行)
- 表结构已在工具描述中给出, 禁止查询sqlite_master/PRAGMA
SQL方言(SQLite, 必须遵守):
- 没有YEAR()/MONTH()/NOW()/FORMAT函数; 年月日用 year/month/day 列, 或 substr(order_date,1,4)='2024'
- year/month/day 是 TEXT 列: 必须用字符串比较如 year='2024'; 写成 year=2024(数字)会查不到任何数据
数据源地图(按问题粒度选表, 避免重复行, 不需要JOIN):
- products: 商品属性, 一行=一个商品, 列: id,name(商品名),category(类目),price(售价),cost(成本)
- orders: 订单头(状态/渠道/客户id/下单时间), 一行=一笔订单
- order_items: 订单明细(件数quantity/成交单价unit_price/折扣discount), 一行=一个明细
- v_sales: 销售明细宽表(一行=一个订单明细), 列清单: order_id,order_date,day,month,year,status,channel,customer_id,customer_name,city,region,vip_level,product_id,product_name,category,price,quantity,unit_price,discount,amount; 注意: 没有单独的 id 列也没有 name 列(订单号=order_id, 商品名=product_name); 适合按维度汇总销售额/件数; 直接列订单会重复
- v_orders: 订单宽表(一行=一笔订单, 含客户/城市/区域/vip/时间/status/channel/item_lines/qty/amount), 用于"前N个订单/订单总数/每单金额"
- v_customers: 客户宽表(一行=一位客户, 含order_count/completed_order_count/completed_amount), 用于客户级统计
- v_product_sales: 商品销售汇总(一行=一个商品, 含qty/line_count/amount/order_count), 用于商品排行
选表规则: 订单级问题用 v_orders; 商品排行用 v_product_sales; 客户统计用 v_customers; 明细/维度汇总用 v_sales; 商品属性用 products。
- 别名用 AS, 字符串用单引号, 不要用反引号
任务: 需要查数据/计算/画图时, 调用工具(一次一步); 闲聊或无需数据时直接文字回答。
计算规则: 对已查到的数值做乘/除/加减/百分比/折扣/倍数运算时, 必须调用 calculator 工具, expression 用上下文中的具体数值组装, 禁止心算。
指标规则: 问销售额/订单量/商品款数/客户数/件数等业务指标时, 优先调用 query_metric——口径由工具自动保证: revenue/qty 自动只算已完成, order_count 自动含全部状态(勿传status), product_count 是商品款数不是销售记录数; 只有长尾问题才用 sqlite_query。实体级排名(如"金额最大的订单/客户/商品")用 query_metric 的 grain=order/customer/product + top=N; 问"已完成订单笔数"用 metric=completed_order_count。需要特殊过滤/JOIN/自定义聚合时直接用 sqlite_query; query_metric 返回空或不支持该口径时, 改用 sqlite_query; 已用 query_metric 得到同一指标的结果后, 不要再用自写SQL覆盖它。
订单状态口径(重要): 销售额/收入/成交金额默认只算已完成(completed); 但"买过/被购买/购买件数/销量/原价销售额/下过单的客户"等历史行为问题默认统计全部订单状态(不加status过滤), 除非题目明确说"已完成"。query_metric 的 revenue/qty 默认 completed, 需要全状态时传 status='all'。
注意: 你有数据库查询能力, 禁止回答"无法访问数据/无法获取实时数据"之类拒绝话术。"""

TOOLS_SPEC = [
    {"type": "function", "function": {
        "name": "sqlite_query",
        "description": "执行只读SQL查询。按粒度选表: products(商品属性)、orders(订单头)、order_items(明细)、v_sales(销售明细宽表,一行=一个明细,按维度汇总用)、v_orders(订单宽表,一行=一笔订单,订单级问题用)、v_customers(客户宽表)、v_product_sales(商品销售汇总,商品排行用)。除v_sales外单表即可回答,无需JOIN。",
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "SQLite SELECT语句"}}, "required": ["sql"]}}},
    {"type": "function", "function": {
        "name": "load_df",
        "description": "把一条简单SELECT的结果加载为沙盒里的 DataFrame(df_1,df_2...), 供 run_python 做 JOIN/聚合/排序/多步计算。只写简单SQL(选列+基本WHERE/LIMIT), 不要多表JOIN/子查询。",
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "简单SELECT语句"}}, "required": ["sql"]}}},
    {"type": "function", "function": {
        "name": "run_python",
        "description": "执行pandas/matplotlib代码。已预置pd,np,plt,conn(sqlite连接),out_dir(图目录); 严禁import和connect; 8行内; 最后print结果; 图用plt.savefig(out_dir+'/文件名')",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "make_chart",
        "description": "画图工具(推荐)。参数: type(line折线/bar柱状/pie饼/hist直方), dim(分组维度: month/year/day/region/category/status/channel/city/vip_level, hist时为price/quantity/amount), metric(count数量/amount销售额/quantity件数/price价格), filters(可选对象, 如{\"year\":2024,\"status\":\"completed\",\"category\":\"数码\"}), filename(如chart_01.png)",
        "parameters": {"type": "object", "properties": {
            "type": {"type": "string"}, "dim": {"type": "string"},
            "metric": {"type": "string"}, "filters": {"type": "object"},
            "filename": {"type": "string"}},
            "required": ["type", "dim", "metric"]}}},
    {"type": "function", "function": {
        "name": "query_metric",
        "description": "业务指标查询(推荐, 口径自动保证, 优先于手写SQL)。metric与口径: revenue=销售额(默认只算已完成订单)/order_count=订单笔数(默认含全部状态)/qty=销售件数(默认只算已完成)/completed_order_count=已完成订单笔数/product_count=商品款数(不是销售记录数)/customer_count=客户数/avg_price=平均成交单价(unit_price)/avg_list_price=商品表售价均值(products.price); 需要全状态(含已取消)时传 status='all'。dim分组: month/year/region/category/channel/city/status/vip_level或none。year仅填问题中出现的年份如\"2024\"。limit=取前N行; grain=order/customer/product 时做实体级Top-N排名(配top=N)",
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string"}, "dim": {"type": "string"},
            "grain": {"type": "string"}, "top": {"type": "integer"},
            "year": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["metric"]}}},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "数值计算器(推荐)。对上下文中已查到的数值做乘/除/加减/百分比/折扣/倍数运算时必须用本工具, 不要心算。expression用具体数值组装, 如 \"12314323.26/94458744.54*100\" 或 \"4850*2\" 或 \"500*0.8\"",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string"}}, "required": ["expression"]}}},
]

_ANSWER_BASE = """你是数据分析回答器。只依据给定的查询结果回答用户问题。
规则: 第一行输出 FINAL; 答案必须包含具体数字或文本结果; 数字不要用万/亿, 按题目要求保留小数; 结果里没有的信息不要编造; 若结果是错误信息(error)则回答 查询失败+原因。
若结果是多行列表, 必须逐行完整列出全部行(不要只列第一行或做摘要)。"""
_ANSWER_SIMPLE = "若多条工具结果内容冲突, 选择能回答问题且最完整的一条(通常行数最多); 不要用中间探查的小结果覆盖完整结果, 若最后一条是空结果/错误则参考前面成功的结果。若 calculator 已给出计算结果, 直接采用该结果作答, 不要再说无法计算。"
_ANSWER_RICH = "选结果优先级: ①同一指标多次查询时, 以最后一次成功的查询为准(修订优先); ②问题要求列表时, 选行数最多且字段匹配的成功结果; ③忽略 SELECT * ... LIMIT 小数字 这类探查性结果, 不要用它回答; ④若最后一条是0行/错误, 用前一条成功结果。若 calculator 已给出计算结果, 直接采用该结果作答, 不要再说无法计算。"
# 观测上下文丰富化: 强模型(ANSWER_CTX=1)增益, 4B 默认简版(避免提示截断)
ANSWER_SYS = _ANSWER_BASE + "\n" + (_ANSWER_RICH if os.environ.get("ANSWER_CTX") == "1" else _ANSWER_SIMPLE)


def parse_tool_call(out):
    """宽容解析1B的准JSON工具调用(r"前缀/漏引号/垃圾前缀/坏转义)"""
    # RWKV/llama.cpp 风格: <tool_calls>[{"name":...,"arguments":{...}}]</tool_calls>
    mtc = re.search(r"<tool_calls>\s*(\[.*?\])\s*</tool_calls>", out or "", re.S)
    if mtc:
        try:
            arr = json.loads(mtc.group(1))
            if isinstance(arr, list) and arr:
                item = arr[0]
                name = item.get("name")
                args = item.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if name:
                    return {"tool": name, "args": args or {}}
        except Exception:
            pass
    m = re.search(r"TOOL", out)
    if not m:
        return None
    tail = out[m.end():].strip()
    tm = re.search(r'"tool"\s*[:：]\s*"(\w+)"', tail)
    tool = tm.group(1) if tm else None
    if tool == "sqlite_query" or (tool is None and "sql" in tail[:120]):
        sm = (re.search(r'"sql"?\s*[:：]\s*r?"(.*?)"\s*\}', tail, re.S)
              or re.search(r'"sql"?\s*[:：]\s*r?"(.*)', tail, re.S))
        if sm:
            sql = sm.group(1).replace('\\"', '"').replace("\\'", "'").replace("\\n", " ")
            sql = re.sub(r"^[^A-Za-z(]*", "", sql)  # 去掉 >>》 之类垃圾前缀
            return {"tool": "sqlite_query", "args": {"sql": sql.strip()}}
    if tool == "run_python":
        cm = (re.search(r'"code"\s*[:：]\s*r?"(.*?)"\s*\}\s*$', tail, re.S)
              or re.search(r'"code"\s*[:：]\s*r?"(.*)', tail, re.S))
        if cm:
            code = cm.group(1).replace('\\"', '"').replace("\\n", "\n").replace("\\'", "'")
            return {"tool": "run_python", "args": {"code": code}}
    try:
        j = json.loads(tail[:tail.rindex("}") + 1])
        if isinstance(j, dict) and "tool" in j:
            return j
    except Exception:
        pass
    return None


class AgentV4(BaseAgent):
    name = "v4_sandbox"
    tools = ("sql", "code")
    schema = False          # schema已内置在规划器提示里
    fewshot = False
    heal = False            # 自愈改为: 代码报错回传规划器
    memory = False
    router = False
    max_tool_rounds = 3

    def force_tool(self, user_text):
        """v6路由器覆写: 数据类问题强制要求工具调用"""
        return False

    def planner_hint(self, user_text):
        """v6覆写: 针对性问题类型的额外提示"""
        return ""

    def empty_retry(self, result):
        """v6覆写: 空结果也触发重试"""
        return False

    def _planner_msgs(self, user_text, observations):
        msgs = [{"role": "system", "content": PLANNER_SYS + self.planner_hint(user_text)}]
        for h in self.history[-4:]:
            msgs.append({"role": "user", "content": h["q"][:200]})
            msgs.append({"role": "assistant", "content": h["a"][:200]})
        content = user_text
        for i, (call, res) in enumerate(observations):
            content += f"\n[第{i+1}次工具调用] {json.dumps(call, ensure_ascii=False)[:200]}\n[结果] {json.dumps(res, ensure_ascii=False)[:600]}"
        if observations:
            content += "\n若以上数据已足够请直接文字回答; 还需不同数据则调用工具。不要重复上一次相同的调用。"
        msgs.append({"role": "user", "content": content[:2000]})
        return msgs

    def _plan_call(self, msgs):
        """原生function calling规划; 返回 (tool_call_dict|None, raw_content)"""
        spec = getattr(self, "tool_spec", TOOLS_SPEC)
        try:
            r = client().chat.completions.create(
                model=MODEL_ID, messages=msgs, temperature=0.0,
                max_tokens=1500, tools=spec)
            msg = r.choices[0].message
            if msg.tool_calls:
                tc = msg.tool_calls[0]
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                return {"tool": tc.function.name, "args": args}, (msg.content or "")
            content = msg.content or ""
            if parse_tool_call(content):
                return parse_tool_call(content), content
            # 部署不识别tools参数(模型自述无工具): 降级文本协议再规划一次
            tools_text = "; ".join(
                f'{t["function"]["name"]}({t["function"]["description"][:80]})'
                for t in spec)
            msgs2 = msgs + [
                {"role": "assistant", "content": content[:400]},
                {"role": "user", "content":
                    f"[系统注入] 本环境已提供以下工具: {tools_text}。"
                    "你必须输出一行 JSON 调用来使用工具, 格式: "
                    'TOOL {"tool":"sqlite_query","args":{"sql":"SELECT ..."}} '
                    '或 TOOL {"tool":"run_python","args":{"code":"..."}}。只输出这一行。'}]
            try:
                r2 = client().chat.completions.create(
                    model=MODEL_ID, messages=msgs2, temperature=0.0,
                    max_tokens=1500, tools=spec)
                m2 = r2.choices[0].message
                if m2.tool_calls:
                    tc = m2.tool_calls[0]
                    try:
                        a2 = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        a2 = {}
                    return {"tool": tc.function.name, "args": a2}, (m2.content or "")
                c2 = m2.content or ""
                if parse_tool_call(c2):
                    return parse_tool_call(c2), c2
                # 最后尝试: 从注入后回复里找 TOOL
                return parse_tool_call((c2 or "") + (content or "")), c2
            except Exception:
                return parse_tool_call(content), content
        except Exception:
            # 服务端原生工具不可用时退回文本协议
            out = strip_fence(chat(msgs, temperature=0.0, max_tokens=1000))
            return parse_tool_call(out), out

    def _answer_msgs(self, user_text, observations):
        content = f"用户问题: {user_text}"
        for i, (call, res) in enumerate(observations):
            content += f"\n[工具{i+1}结果] {json.dumps(res, ensure_ascii=False)[:900]}"
        return [{"role": "system", "content": ANSWER_SYS},
                {"role": "user", "content": content[:2400]}]

    def _retry_call(self, user_text, call, result):
        """单次错误重试: 只带原问题+错误, 不堆历史"""
        content = (f"{user_text}\n[上次工具调用出错] {str(result.get('error'))[:240]}\n"
                   "修正后重新调用工具(列名以v_sales视图字段为准)。")
        try:
            fix, _ = self._plan_call([{"role": "system", "content": PLANNER_SYS},
                                      {"role": "user", "content": content[:1600]}])
            return fix
        except Exception:
            return None

    def ask(self, user_text):
        steps, observations = [], []
        # ---- 阶段A: 规划-执行循环(微任务, 原生工具调用) ----
        for r in range(self.max_tool_rounds):
            try:
                call, raw = self._plan_call(self._planner_msgs(user_text, observations))
            except Exception:
                break
            if call is None:
                # 数据类问题却没调用工具: 强制提醒重试(无产出前每轮升级推动, 直到轮次上限)
                if self.force_tool(user_text) and not observations:
                    try:
                        fmsgs = self._planner_msgs(user_text, observations)
                        fmsgs[-1]["content"] = (fmsgs[-1]["content"][:1800]
                                                + "\n[提示] 该问题必须查询数据库数据才能回答, 你已连接数据库工具, 现在就调用sqlite_query。")
                        call, raw = self._plan_call(fmsgs)
                    except Exception:
                        call = None
                if call is None:
                    break
            if not isinstance(call, dict) or not call.get("tool"):
                break
            # 防重复调用死循环
            if observations and json.dumps(call.get("args"), sort_keys=True) == json.dumps(observations[-1][0].get("args"), sort_keys=True):
                break
            result = self.execute(call, steps)
            steps.append({"tool": call.get("tool"), "args": call, "result": result})
            # 任何工具报错: 单次带错重试; v6: 空结果也重试
            need_retry = (not result.get("ok")) or (self.empty_retry(result) and result.get("empty"))
            if need_retry:
                why = ("查询返回0行。按顺序诊断: ①年份/月份列是TEXT, 必须用字符串如 year='2024', 数字会查不到 ②先用 SELECT DISTINCT 该列看真实取值 ③过滤条件可能过严, 先去条件看基数 ④是否该用宽表 v_sales/是否需要JOIN") if result.get("ok") else str(result.get("error"))[:240]
                fix = self._retry_call(user_text, call, {"error": why})
                if isinstance(fix, dict) and fix.get("tool"):
                    result2 = self.execute(fix, steps)
                    steps.append({"tool": fix.get("tool"), "args": fix, "result": result2})
                    call, result = fix, result2
            observations.append((call, result))
        # ---- 阶段B: 依据结果作答(微任务) ----
        if observations:
            ans = None
            for attempt in range(2):
                try:
                    ans = chat(self._answer_msgs(user_text, observations), temperature=0.0, max_tokens=int(os.environ.get("ANSWER_TOK", "3000")))
                    break
                except Exception:
                    if attempt == 0:
                        import time as _t
                        _t.sleep(1.0)
            if not (ans or "").strip():
                # 空答重试: 部分思考模型会把输出预算烧在思考上, 提示直接作答
                try:
                    msgs2 = self._answer_msgs(user_text, observations)
                    msgs2[-1]["content"] += "\n[要求] 直接输出FINAL和最终答案, 不要重复分析或计算过程。"
                    ans = chat(msgs2, temperature=0.0,
                               max_tokens=int(os.environ.get("ANSWER_TOK", "3000")))
                except Exception:
                    pass
            ans = ans or "(回答失败)"
            m = re.search(r"FINAL[:：]?\s*(.*)", strip_fence(ans), re.S)
            answer = (m.group(1).strip() if m else strip_fence(ans)) or "未获得结果"
        else:
            msgs = [{"role": "system", "content": "你是简洁的助手。"}
                    ] + [{"role": "user", "content": h["q"][:150]} for h in self.history[-4:]] + [
                    {"role": "user", "content": user_text}]
            try:
                answer = chat(msgs, temperature=0.0, max_tokens=1500)
            except Exception:
                answer = "(回答失败)"

        self.history.append({"q": user_text, "a": answer})
        self.after_turn(user_text, answer, steps)
        self.trace.append({"turn": len(self.history), "user": user_text, "steps": steps, "answer": answer})
        return answer
