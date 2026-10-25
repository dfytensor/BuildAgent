# -*- coding: utf-8 -*-
"""v11d 直测: status='all' + 全状态排名"""
import sys
sys.path.insert(0, "agent")
from query_metric import tool_query_metric

print("== revenue 默认(completed) vs all ==")
print(" done:", tool_query_metric({"metric": "revenue"}, {}).get("rows"))
print(" all :", tool_query_metric({"metric": "revenue", "status": "all"}, {}).get("rows"))

print("\n== qty grain=customer top1 默认 vs all (T5-02: 期望all->175/426) ==")
print(" done:", tool_query_metric({"metric": "qty", "grain": "customer", "top": 3}, {}).get("rows"))
print(" all :", tool_query_metric({"metric": "qty", "grain": "customer", "top": 3, "status": "all"}, {}).get("rows"))

print("\n== L8-02: 数码商品购买件数 all(期望1132) ==")
r = tool_query_metric({"metric": "qty", "grain": "product", "top": 3, "status": "all",
                       "filters": {"category": "数码"}}, {})
print(" ", r.get("rows"))
