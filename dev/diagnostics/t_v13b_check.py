# -*- coding: utf-8 -*-
"""v13b 机制自检: 路径判定 + load_df + 命名空间复用"""
import sys
sys.path.insert(0, "agent")
from v13b_hybrid2 import AgentV13B

ag = AgentV13B()
print("path(每月订单数):", ag._choose_path("2024年每月的订单数"))
print("path(渠道占比):", ag._choose_path("各渠道销售额占总销售额的百分比"))

r1 = ag.sandbox.load("SELECT order_id, qty, amount FROM v_orders LIMIT 5", {"session_id": "t", "trace": []})
print("load_df ->", {k: r1.get(k) for k in ("ok", "df", "rows", "columns")})

r2 = ag.sandbox.run({"code": "print(df_1['amount'].sum())"}, {"session_id": "t", "trace": []})
print("run_python ->", r2)
ag.cleanup()
