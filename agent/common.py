# -*- coding: utf-8 -*-
"""公共设施: LLM客户端 / sqlite工具 / pandas+matplotlib沙盒 / 溯源存储 / schema注入"""
import os
import re
import json
import time
import sqlite3
import subprocess
import sys

from openai import OpenAI

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "shop.db")
ARTIFACTS = os.path.join(BASE, "artifacts")
TRACE_DIR = os.path.join(ARTIFACTS, "trace")
os.makedirs(TRACE_DIR, exist_ok=True)

BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
MODEL_ID = os.environ.get("LLM_MODEL", "spark-x2.6-4b-lossless")
API_KEY = os.environ.get("LLM_API_KEY", "none")
EXTRA_BODY = json.loads(os.environ.get("LLM_EXTRA_BODY", '{"chat_template_kwargs": {"enable_thinking": false}}'))
TOK_CAP = int(os.environ.get("LLM_TOK_CAP", "3000"))

_client = None


def client():
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=480, max_retries=0)
    return _client


def chat(messages, temperature=0.0, max_tokens=512):
    """带重试的对话调用"""
_last_call = [0.0]


def chat(messages, temperature=0.0, max_tokens=512):
    """带重试的对话调用; CHAT_MIN_INTERVAL 秒最小调用间隔(限流合规)"""
    # 小窗口部署保护: 总提示字符钳制(防 prompt+output 超上下文触发服务端 assert)
    max_chars = int(os.environ.get("LLM_MAX_PROMPT_CHARS", "100000") or 100000)
    est = sum(len(str(m.get('content', ''))) for m in messages)
    if est > max_chars:
        head = sum(len(str(m.get('content', ''))) for m in messages[:-1])
        last = dict(messages[-1])
        last['content'] = str(last.get('content', ''))[:max(200, max_chars - head)]
        messages = messages[:-1] + [last]
    min_iv = float(os.environ.get("CHAT_MIN_INTERVAL", "0") or 0)
    if min_iv > 0:
        wait = _last_call[0] + min_iv - time.time()
        if wait > 0:
            time.sleep(wait)
    for attempt in range(6):
        try:
            _last_call[0] = time.time()
            r = client().chat.completions.create(
                model=MODEL_ID, messages=messages,
                temperature=temperature,
                max_tokens=min(max_tokens, TOK_CAP),
                extra_body=EXTRA_BODY or None, stream=False)
            return r.choices[0].message.content or ""
        except Exception as e:
            if attempt == 5:
                try:
                    _d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "_tmp_cases")
                    os.makedirs(_d, exist_ok=True)
                    with open(os.path.join(_d, "llm_errs.log"), "a", encoding="utf-8") as _f:
                        _f.write(f"{time.strftime('%m-%d %H:%M:%S')} {type(e).__name__}: {str(e)[:220]}\n")
                except Exception:
                    pass
                raise
            # 429 窗口抓取: 固定25s退避(免费池拥挤时持续敲门)
            time.sleep(25.0 if "429" in str(e) else 2.0)


# ---------------- schema 注入(压缩版, 省token) ----------------
SCHEMA_TEXT = """库:SQLite shop.db(电商)
customers(id,name姓名,city城市,region区域[华东/华北/华南/西南/东北],signup_date注册日,vip_level 0-3)
products(id,name,category类目[数码/家电/服饰/食品/美妆/家居],price售价,cost成本)
orders(id,customer_id→customers.id,order_date如2024-06-15 13:22:10,status[completed已完成/cancelled已取消/pending待处理],channel[app/web/mini_program小程序])
order_items(id,order_id→orders.id,product_id→products.id,quantity件数,unit_price成交单价,discount折扣0~0.2)
销售额=SUM(quantity*unit_price*(1-discount)); 只统计已完成订单须加 orders.status='completed'"""


def summarize_result(res, max_rows=50, max_chars=3000):
    """工具结果呈现(供回答器): 列名 + 全量数据行; 绝不生成派生数字; 任何异常都不许抛出"""
    try:
        return _summarize_result(res, max_rows, max_chars)
    except Exception:
        return str(res)[:max_chars]


def _summarize_result(res, max_rows=50, max_chars=3000):
    if not isinstance(res, dict):
        return str(res)[:max_chars]
    if not res.get("ok", False):
        return "错误: " + str(res.get("error"))[:300]
    if res.get("schema"):
        return "schema探查: 已返回库结构(提示词中已有), 无需重复探查"
    cols = res.get("columns")
    cols = cols if isinstance(cols, list) else []
    rows = res.get("rows")
    rows = rows if isinstance(rows, list) else []  # make_chart 的 rows 是行数(int), 不按行呈现
    parts = []
    if cols:
        parts.append("列: " + ", ".join(str(c) for c in cols))
    if rows or cols:
        parts.append("数据: " + json.dumps(rows[:max_rows], ensure_ascii=False))
        if len(rows) > max_rows:
            parts.append(f"(仅显示前{max_rows}行, 共{len(rows)}行)")
    for k in ("note", "empty", "saved", "stdout"):
        if res.get(k):
            parts.append(f"{k}: {str(res[k])[:200]}")
    return " | ".join(parts)[:max_chars]

# ---------------- 工具实现 ----------------


def tool_sqlite_query(args: dict, state: dict):
    sql = str(args.get("sql", "")).strip()
    if not sql:
        return {"ok": False, "error": "sql为空"}
    # schema探查拦截: 直接返回完整结构, 不占用执行轮次
    up = sql.upper()
    if "SQLITE_MASTER" in up or up.startswith("PRAGMA"):
        return {"ok": True, "schema": SCHEMA_TEXT,
                "note": "库结构如上(含宽表v_sales全部列)。直接写业务SQL即可, 无需再探查结构。"}
    for kw in ("DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "ATTACH"):
        if kw in sql.upper().split():
            return {"ok": False, "error": f"禁止{kw}操作"}
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(sql)
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            truncated = len(rows) > 50
            rows = rows[:50]
            out = {"ok": True, "columns": cols, "rows": [[round(c, 4) if isinstance(c, float) else c for c in rows[r]] for r in range(len(rows))]}
            if not rows:
                out["empty"] = True
                out["note"] = "查询成功但结果为0行"
            if truncated:
                out["note"] = f"仅显示前50行(共{len(rows)}+行)"
        else:
            conn.commit()
            out = {"ok": True, "rows_affected": cur.rowcount}
        conn.close()
        return out
    except sqlite3.OperationalError as e:
        msg = str(e)
        if "no such column" in msg or "no such table" in msg:
            hint = "可用列(v_sales): " + ", ".join(CHART_DIMS.keys()) + ", amount, unit_price, discount, price, product_name, customer_name, order_id, product_id, customer_id, status, channel, region, city, category, vip_level"
            return {"ok": False, "error": f"{msg}。{hint}"}
        return {"ok": False, "error": msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_SANDBOX_CHILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_child.py")


def tool_run_python(args: dict, state: dict):
    code = args.get("code", "")
    if not code.strip():
        return {"ok": False, "error": "code为空"}
    # 静态黑名单拦截(演示级沙盒)
    banned = ("subprocess", "socket", "shutil", "os.system", "os.popen", "__import__", "eval(", "exec(")
    for b in banned:
        if b in code:
            return {"ok": False, "error": f"代码包含被禁止的调用: {b}"}
    task = {"code": code, "db": DB_PATH, "out_dir": ARTIFACTS}
    if args.get("_ns_file"):
        task["_ns_file"] = args["_ns_file"]
    if args.get("keep_ns"):
        task["keep_ns"] = True
    task_id = len(state.get("trace", []))
    tfile = os.path.join(TRACE_DIR, f"_task_{state.get('session_id', 'x')}_{task_id}.json")
    with open(tfile, "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False)
    try:
        p = subprocess.run([sys.executable, "-X", "utf8", _SANDBOX_CHILD, tfile],
                           capture_output=True, text=True, encoding="utf-8", timeout=90)
        out = p.stdout.strip()
        try:
            return json.loads(out)
        except Exception:
            return {"ok": p.returncode == 0, "stdout": out[-1500:], "error": (p.stderr or "")[-800:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "执行超时(90s)"}


class SandboxSession:
    """有状态的沙盒: 同一会话内变量保留(避免每轮重复加载数据, 也支持多步分析)"""

    def __init__(self):
        self._ns_file = os.path.join(TRACE_DIR, f"_ns_{id(self)}.pkl")
        self.calls = 0
        self.df_seq = 0

    def run(self, args, state):
        self.calls += 1
        args = dict(args)
        args["_ns_file"] = self._ns_file
        args["keep_ns"] = True
        return tool_run_python(args, state)

    def load(self, sql, state):
        """把一条简单SELECT加载为沙盒DataFrame(df_1,df_2...), 供 run_python 做复杂处理"""
        sql = str(sql or "").strip()
        if not sql:
            return {"ok": False, "error": "sql为空"}
        self.df_seq += 1
        name = f"df_{self.df_seq}"
        no_head = os.environ.get("LOAD_DF_NO_HEAD") == "1"
        code = (
            "import json as _json\n"
            f"{name} = pd.read_sql({sql!r}, conn)\n"
            f"_info = {{'df': {name!r}, 'columns': [str(c) for c in {name}.columns], 'rows': int(len({name}))}}\n"
            f"if {not no_head}:\n"
            f"    _info['head'] = {name}.head(3).to_dict('records')\n"
            "print(_json.dumps(_info, ensure_ascii=False, default=str))\n"
        )
        res = self.run({"code": code}, state)
        try:
            inner = json.loads(res.get("stdout") or "")
            res.update(inner)
        except Exception:
            pass
        res["df"] = name
        return res

    def cleanup(self):
        try:
            os.remove(self._ns_file)
        except OSError:
            pass


# ---------------- make_chart: 槽位填充式绘图(小模型只需填参, SQL/绘图由代码组装) ----------------
CHART_DIMS = {"month": "month", "year": "year", "day": "day", "region": "region",
              "category": "category", "status": "status", "channel": "channel",
              "city": "city", "vip_level": "vip_level"}


def tool_calculator(args: dict, state: dict):
    """确定性算术执行器: 模型只组装表达式(从上下文抄数值), 代码 AST 白名单求值"""
    import ast
    expr = str(args.get("expression", "")).strip()
    if not expr:
        return {"ok": False, "error": "expression为空"}
    expr = (expr.replace("×", "*").replace("÷", "/")
                .replace("，", ",").replace("＝", "="))
    expr = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", expr)
    try:
        node = ast.parse(expr, mode="eval")
    except Exception as e:
        return {"ok": False, "error": f"表达式语法错误: {type(e).__name__}: {e}"}
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add,
               ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Pow,
               ast.Call, ast.Name, ast.Load)
    SAFE_FUNCS = {"round": round, "abs": abs, "min": min, "max": max,
                  "sum": sum, "int": int, "float": float, "pow": pow}
    for n in ast.walk(node):
        if not isinstance(n, allowed):
            return {"ok": False, "error": f"不允许的语法: {type(n).__name__}"}
        if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float)):
            return {"ok": False, "error": "只允许数字常量"}
        if isinstance(n, ast.Name) and n.id not in SAFE_FUNCS:
            return {"ok": False, "error": f"未知标识符: {n.id}"}
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id not in SAFE_FUNCS:
                return {"ok": False, "error": f"只允许安全函数: {sorted(SAFE_FUNCS)}"}
    try:
        val = round(float(eval(compile(node, "<calc>", "eval"),
                               {"__builtins__": {}}, SAFE_FUNCS)), 4)
    except Exception as e:
        return {"ok": False, "error": f"求值失败: {type(e).__name__}: {e}"}
    return {"ok": True, "expression": expr, "value": val}
CHART_METRICS = {"count": "COUNT(*)", "amount": "ROUND(SUM(amount),2)",
                 "quantity": "SUM(quantity)", "price": "AVG(price)"}
CHART_FILTERS = {"year": "year", "month": "month", "status": "status", "channel": "channel",
                 "region": "region", "city": "city", "category": "category", "vip_level": "vip_level"}


def tool_make_chart(args: dict, state: dict):
    ctype = (args.get("type") or "bar").lower()
    dim = (args.get("dim") or "month").lower()
    metric = (args.get("metric") or "count").lower()
    filters = args.get("filters") or {}
    filename = args.get("filename") or f"chart_auto_{int(time.time()) % 100000}.png"
    if ctype not in ("line", "bar", "pie", "hist"):
        return {"ok": False, "error": f"type须为 line/bar/pie/hist, 得到 {ctype}"}
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False

        conn = sqlite3.connect(DB_PATH)
        if ctype == "hist":
            col = dim if dim in ("price", "quantity", "amount") else "price"
            df = pd.read_sql(f"SELECT {col} AS v FROM v_sales", conn)
            plt.figure(figsize=(7, 4))
            plt.hist(df["v"].dropna(), bins=30)
            plt.title(f"{col} 分布")
        else:
            if dim not in CHART_DIMS:
                return {"ok": False, "error": f"dim须为 {list(CHART_DIMS)}, 得到 {dim}"}
            if metric not in CHART_METRICS:
                return {"ok": False, "error": f"metric须为 {list(CHART_METRICS)}, 得到 {metric}"}
            where, params = [], []
            for k, v in filters.items():
                if k in CHART_FILTERS:
                    # year/month/day 是 TEXT 列(substr生成), 数值须转字符串比较; vip_level为INTEGER
                    if k in ("year", "month", "day"):
                        v = str(v)
                    elif k == "vip_level" and isinstance(v, str) and v.isdigit():
                        v = int(v)
                    where.append(f"{k} = ?")
                    params.append(v)
            sql = (f"SELECT {CHART_DIMS[dim]} AS label, {CHART_METRICS[metric]} AS value "
                   f"FROM v_sales")
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += f" GROUP BY {CHART_DIMS[dim]} ORDER BY {CHART_DIMS[dim]}"
            df = pd.read_sql(sql, conn, params=params)
            labels = df["label"].astype(str)
            values = pd.to_numeric(df["value"], errors="coerce")
            plt.figure(figsize=(8, 4.5))
            if ctype == "line":
                plt.plot(labels, values, marker="o")
            elif ctype == "bar":
                plt.bar(labels, values)
            else:
                plt.pie(values, labels=labels, autopct="%.1f%%")
                plt.axis("equal")
            plt.title(f"{metric} by {dim}")
            plt.xticks(rotation=45, fontsize=8)
            plt.tight_layout()
        path = os.path.join(ARTIFACTS, filename)
        plt.savefig(path, dpi=110)
        plt.close()
        conn.close()
        if os.path.getsize(path) < 3000:
            return {"ok": False, "error": "图片生成异常(过小)"}
        return {"ok": True, "saved": path, "note": "图已生成", "rows": len(df)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
