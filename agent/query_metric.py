# -*- coding: utf-8 -*-
"""query_metric: 语义层/指标注册表工具(v10核心)
业务口径在此统一定义(数据字典), 模型只填槽:
  revenue      销售额   = SUM(quantity*unit_price*(1-discount)), 默认已完成订单口径(BI惯例)
  order_count  订单笔数 = COUNT(DISTINCT order_id), 含所有状态(除非显式给status)
  qty          销售件数 = SUM(quantity)
  avg_price    平均成交单价 = AVG(unit_price)
  product_count 商品款数(products表, 不是销售行数!)
  customer_count 客户数(customers表)
维度: month/year/region/category/channel/city/status/vip_level/none
这消除三类小模型高发错误: 口径不一致(隐式排除cancelled)/粒度混淆(商品数vs销售行数)/列名幻觉
"""
import sqlite3

from common import DB_PATH

METRICS_VS = {
    "revenue": ("ROUND(SUM(quantity*unit_price*(1-discount)),2)", "销售额(默认已完成订单口径)"),
    "order_count": ("COUNT(DISTINCT order_id)", "订单笔数(默认含所有状态)"),
    "qty": ("SUM(quantity)", "销售件数"),
    "avg_price": ("ROUND(AVG(unit_price),2)", "平均成交单价"),
    "completed_order_count": ("COUNT(DISTINCT order_id)", "已完成订单笔数"),
}
COUNT_TABLES = {
    "product_count": "products",
    "customer_count": "customers",
}
GRAINS = {
    "order": ("order_id", ""),
    "customer": ("customer_id", ", customer_name"),
    "product": ("product_id", ", product_name"),
}


def _rank_entities(metric, grain, top, year, filters, status=None):
    """实体级 Top-N 排名(通用BI操作): 按 metric 聚合到实体粒度, 降序取前N"""
    key, extra = GRAINS[grain]
    if metric in ("revenue", "amount"):
        agg, default_status = "SUM(quantity*unit_price*(1-discount))", "completed"
    elif metric == "qty":
        agg, default_status = "SUM(quantity)", "completed"
    elif metric == "completed_order_count":
        agg, default_status = "COUNT(DISTINCT order_id)", "completed"
    elif metric in ("order_count", "count"):
        agg, default_status = "COUNT(DISTINCT order_id)", None
    else:
        return {"ok": False, "error": f"排名不支持的metric: {metric}"}
    if status == "all":
        eff_status = None
    elif status not in (None, ""):
        eff_status = status
    else:
        eff_status = default_status
    where, params = [], []
    if eff_status:
        where.append("status = ?")
        params.append(eff_status)
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


DIMS = {"month": "month", "year": "year", "region": "region", "category": "category",
        "channel": "channel", "city": "city", "status": "status", "vip_level": "vip_level"}
FILTERS = {"year": "year", "month": "month", "status": "status", "channel": "channel",
           "region": "region", "city": "city", "category": "category", "vip_level": "vip_level",
           "product_name": "product_name", "customer_name": "customer_name"}


def tool_query_metric(args: dict, state: dict):
    grain = str(args.get("grain") or "").strip().lower()
    if grain:
        if grain not in GRAINS:
            return {"ok": False, "error": f"grain须为{sorted(GRAINS)}"}
        return _rank_entities(str(args.get("metric", "")).strip().lower(), grain,
                              args.get("top"), args.get("year"), args.get("filters") or {},
                              args.get("status"))
    metric = str(args.get("metric", "")).strip()
    dim = str(args.get("dim") or "none").lower()
    limit = int(args.get("limit") or 0)
    top = int(args.get("top") or 0)
    filters = args.get("filters") or {}
    year = args.get("year")
    status = args.get("status")

    if metric in COUNT_TABLES:
        table = COUNT_TABLES[metric]
        where, params = [], []
        for k, v in (filters or {}).items():
            if k in FILTERS and k in ("category",) if table == "products" else k in ("region", "city", "vip_level"):
                where.append(f"{k} = ?")
                params.append(int(v) if k == "vip_level" and str(v).isdigit() else v)
        if dim != "none" and dim not in DIMS:
            return {"ok": False, "error": f"dim须为{sorted(DIMS)}"}
        sql = f"SELECT {dim} AS label, COUNT(*) AS value FROM {table}" if dim != "none" else \
              f"SELECT COUNT(*) AS value FROM {table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        if dim != "none":
            sql += f" GROUP BY {dim} ORDER BY {dim}"
        cur = sqlite3.connect(DB_PATH).execute(sql, params)
        rows = [tuple(r) for r in cur.fetchall()]
        return {"ok": True, "metric": metric, "columns": ["label", "value"], "rows": rows[:50],
                "note": "口径: 见工具描述"}

    if metric not in METRICS_VS:
        return {"ok": False, "error": f"metric须为 {sorted(list(METRICS_VS) + list(COUNT_TABLES))}, 得到 {metric}"}
    agg = METRICS_VS[metric][0]
    if dim != "none" and dim not in DIMS:
        return {"ok": False, "error": f"dim须为{sorted(DIMS)}, 得到 {dim}"}
    where, params = [], []
    # 房间口径: 销售额默认只统计已完成订单(可用status覆盖; status='all'=全部状态)
    if status == "all":
        eff_status = None
    else:
        eff_status = status if status not in (None, "") else ("completed" if metric in ("revenue", "completed_order_count") else None)
    if eff_status:
        where.append("status = ?")
        params.append(eff_status)
    if year not in (None, "", "all"):
        where.append("year = ?")
        params.append(str(year))
    for k, v in (filters or {}).items():
        k = str(k).lower()
        if k in FILTERS and k not in ("year", "status"):
            where.append(f"{k} = ?")
            params.append(int(v) if k == "vip_level" and str(v).isdigit() else v)
    if dim != "none":
        sql = f"SELECT {dim} AS label, {agg} AS value FROM v_sales"
    else:
        sql = f"SELECT {agg} AS value FROM v_sales"
    if where:
        sql += " WHERE " + " AND ".join(where)
    if dim != "none":
        sql += f" GROUP BY {dim} ORDER BY {dim}"
    try:
        cur = sqlite3.connect(DB_PATH).execute(sql, params)
        rows = [tuple(r) for r in cur.fetchall()]
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    out = {"ok": True, "metric": metric, "columns": (["label", "value"] if dim != "none" else ["value"]),
           "rows": rows[:50], "note": METRICS_VS[metric][1] + (f", {eff_status}" if eff_status and metric == 'revenue' else "")}
    if not rows:
        out["empty"] = True
    if top > 0 and dim != "none":
        try:
            rows_sorted = sorted(rows, key=lambda r: float(r[1]) if r[1] is not None else 0, reverse=True)[:top]
            out["rows"] = rows_sorted
            out["note"] += f", 已按值降序取前{top}"
        except Exception:
            pass
    return out
