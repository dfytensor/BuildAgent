# -*- coding: utf-8 -*-
"""v11c: 语义层 v2
1) query_metric 增加实体级排名 grain(order/customer/product) + top=N
2) 增加 completed_order_count 指标(已完成订单笔数, 月度/类目通用)
3) PLANNER_SYS 增加回退指引: metric 不适用/空结果时改裸 SQL
"""
import pathlib

# ---------- 1) query_metric ----------
q = pathlib.Path(r"agent\query_metric.py")
t = q.read_text(encoding="utf-8")

old_metrics = '    "avg_price": ("ROUND(AVG(unit_price),2)", "平均成交单价"),'
new_metrics = ('    "avg_price": ("ROUND(AVG(unit_price),2)", "平均成交单价"),\n'
               '    "completed_order_count": ("COUNT(DISTINCT order_id)", "已完成订单笔数"),')
assert old_metrics in t, "METRICS_VS anchor not found"
t = t.replace(old_metrics, new_metrics, 1)

old_status = 'eff_status = status if status not in (None, "", "all") else ("completed" if metric == "revenue" else None)'
new_status = ('eff_status = status if status not in (None, "", "all") else '
              '("completed" if metric in ("revenue", "completed_order_count") else None)')
assert old_status in t, "eff_status line not found"
t = t.replace(old_status, new_status, 1)

anchor = 'DIMS = {"month": "month", "year": "year", "region": "region", "category": "category",\n'
assert anchor in t, "DIMS anchor not found"
rank_impl = '''GRAINS = {
    "order": ("order_id", ""),
    "customer": ("customer_id", ", customer_name"),
    "product": ("product_id", ", product_name"),
}


def _rank_entities(metric, grain, top, year, filters):
    """实体级 Top-N 排名(通用BI操作): 按 metric 聚合到实体粒度, 降序取前N"""
    key, extra = GRAINS[grain]
    if metric in ("revenue", "amount"):
        agg, status = "SUM(quantity*unit_price*(1-discount))", "completed"
    elif metric == "qty":
        agg, status = "SUM(quantity)", "completed"
    elif metric == "completed_order_count":
        agg, status = "COUNT(DISTINCT order_id)", "completed"
    elif metric in ("order_count", "count"):
        agg, status = "COUNT(DISTINCT order_id)", None
    else:
        return {"ok": False, "error": f"排名不支持的metric: {metric}"}
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    if year not in (None, "", "all"):
        where.append("year = ?")
        params.append(str(year))
    for k, v in (filters or {}).items():
        k = str(k).lower()
        if k in FILTERS and k not in ("year", "status"):
            where.append(f"{k} = ?")
            params.append(int(v) if k == "vip_level" and str(v).isdigit() else v)
    cols = [key] + ([extra.strip(", ")] if extra else []) + ["value"]
    sql = f"SELECT {key}{extra}, ROUND({agg}, 2) AS value FROM v_sales"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" GROUP BY {key}{extra} ORDER BY value DESC LIMIT ?"
    params.append(max(1, min(int(top or 5), 50)))
    try:
        rows = [tuple(r) for r in sqlite3.connect(DB_PATH).execute(sql, params).fetchall()]
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "metric": metric, "grain": grain, "columns": cols, "rows": rows,
            "note": f"按{grain}聚合的Top-N排名({metric})"}


'''
t = t.replace(anchor, rank_impl + anchor, 1)

hook = 'def tool_query_metric(args: dict, state: dict):\n'
assert hook in t
branch = '''def tool_query_metric(args: dict, state: dict):
    grain = str(args.get("grain") or "").strip().lower()
    if grain:
        if grain not in GRAINS:
            return {"ok": False, "error": f"grain须为{sorted(GRAINS)}"}
        return _rank_entities(str(args.get("metric", "")).strip().lower(), grain,
                              args.get("top"), args.get("year"), args.get("filters") or {})
'''
t = t.replace(hook, branch, 1)
q.write_text(t, encoding="utf-8")

# ---------- 2) PLANNER_SYS + 工具描述 ----------
v = pathlib.Path(r"agent\v4_sandbox.py")
t2 = v.read_text(encoding="utf-8")
old = "只有长尾问题才用 sqlite_query。"
new = ("只有长尾问题才用 sqlite_query。实体级排名(如\"金额最大的订单/客户/商品\")用 query_metric 的 "
       "grain=order/customer/product + top=N; 问\"已完成订单笔数\"用 metric=completed_order_count。"
       "需要特殊过滤/JOIN/自定义聚合时直接用 sqlite_query; query_metric 返回空或不支持该口径时, "
       "改用 sqlite_query, 不要重复同一调用。")
assert old in t2, "planner metric rule not found"
t2 = t2.replace(old, new)

old3 = '"metric": {"type": "string"}, "dim": {"type": "string"},'
new3 = ('"metric": {"type": "string"}, "dim": {"type": "string"},\n'
        '            "grain": {"type": "string"}, "top": {"type": "integer"},')
assert old3 in t2, "query_metric params not found"
t2 = t2.replace(old3, new3, 1)
old4 = "limit=取前N行\""
new4 = "limit=取前N行; grain=order/customer/product 时做实体级Top-N排名(配top=N)\""
assert old4 in t2, "query_metric desc not found"
t2 = t2.replace(old4, new4, 1)
v.write_text(t2, encoding="utf-8")
print("v11c patched: entity ranking + completed_order_count + fallback guidance")
