# -*- coding: utf-8 -*-
"""黄金/视图疑点查证"""
import json
import sqlite3

conn = sqlite3.connect(r"data\shop.db")
cases = json.load(open(r"eval\cases.json", encoding="utf-8"))
cmap = {}
for s, lst in cases.items():
    for c in lst:
        cmap[c["id"]] = c

print("== 1. SQL-L8-02: v_sales vs order_items 每商品件数 ==")
a = conn.execute("""SELECT p.id, p.name, SUM(i.quantity) FROM products p
                    JOIN order_items i ON i.product_id=p.id WHERE p.category='数码'
                    GROUP BY p.id ORDER BY p.id LIMIT 3""").fetchall()
b = conn.execute("""SELECT product_id, product_name, SUM(quantity) FROM v_sales
                    WHERE category='数码' GROUP BY product_id ORDER BY product_id LIMIT 3""").fetchall()
print(" order_items:", a)
print(" v_sales    :", b)
print(" 全表对比:", conn.execute("SELECT (SELECT SUM(quantity) FROM order_items), (SELECT SUM(quantity) FROM v_sales)").fetchone())

print("\n== 2. TOOL-T5-02: 买过最多件商品的客户 ==")
print(" order_items 全状态:", conn.execute("""SELECT o.customer_id, SUM(i.quantity) q FROM order_items i
        JOIN orders o ON o.id=i.order_id GROUP BY o.customer_id ORDER BY q DESC LIMIT 3""").fetchall())
print(" v_sales 已完成:", conn.execute("""SELECT customer_id, SUM(quantity) q FROM v_sales
        WHERE status='completed' GROUP BY customer_id ORDER BY q DESC LIMIT 3""").fetchall())
print(" gold:", cmap["TOOL-T5-02"].get("turns", {}).get("turns", [{}])[0].get("gold"))

print("\n== 3. TOOL-T2-10: 智能手机1号/冰箱1号 客户数 ==")
print(" 全状态:", conn.execute("""SELECT p.name, COUNT(DISTINCT o.customer_id) FROM order_items i
        JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id
        WHERE p.name IN ('智能手机1号','冰箱1号') GROUP BY p.name""").fetchall())
print(" 已完成:", conn.execute("""SELECT p.name, COUNT(DISTINCT o.customer_id) FROM order_items i
        JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id
        WHERE p.name IN ('智能手机1号','冰箱1号') AND o.status='completed' GROUP BY p.name""").fetchall())

print("\n== 4. TOOL-T5-03: 2024-11 金额/订单数 ==")
print(" 完成金额:", conn.execute("SELECT ROUND(SUM(quantity*unit_price*(1-discount)),2) FROM v_sales WHERE year='2024' AND month='2024-11' AND status='completed'").fetchone())
print(" 完成订单数:", conn.execute("SELECT COUNT(DISTINCT order_id) FROM v_sales WHERE year='2024' AND month='2024-11' AND status='completed'").fetchone())
print(" 全部订单数:", conn.execute("SELECT COUNT(DISTINCT order_id) FROM v_sales WHERE year='2024' AND month='2024-11'").fetchone())
print(" gold:", cmap["TOOL-T5-03"].get("turns", {}).get("turns", [{}])[-1].get("gold"))

print("\n== 5. TOOL-T5-04: 收纳箱1号 原价销售额 ==")
print(" 全状态:", conn.execute("SELECT ROUND(SUM(quantity*unit_price*(1-discount)),2) FROM v_sales WHERE product_name='收纳箱1号'").fetchone())
print(" 已完成:", conn.execute("SELECT ROUND(SUM(quantity*unit_price*(1-discount)),2) FROM v_sales WHERE product_name='收纳箱1号' AND status='completed'").fetchone())
print(" 原价(quantity*price)全状态:", conn.execute("SELECT ROUND(SUM(quantity*price),2) FROM v_sales WHERE product_name='收纳箱1号'").fetchone())
print(" gold:", cmap["TOOL-T5-04"].get("turns", {}).get("turns", [{}])[-1].get("gold"))

print("\n== 6. 题面 ref_sql 检查(ORDER BY?) ==")
for cid in ("SQL-L6-04", "SQL-L7-01", "SQL-L7-02", "PY-P3-11", "PY-P2-07", "PY-P1-04", "TOOL-T2-03"):
    g = cmap[cid].get("gold") or {}
    ref = g.get("ref_sql") or g.get("ref_py") or ""
    print(f" {cid}: {ref[:200]}")
    if g.get("values"):
        print(f"   gold={g['values'][:8]}")
