# -*- coding: utf-8 -*-
"""v1.1 修正黄金的候选值计算(只读)"""
import sqlite3

conn = sqlite3.connect(r"data\shop.db")

print("== SQL-L6-04 买过数码的客户(按id序前15) ==")
print([r[0] for r in conn.execute("""
SELECT DISTINCT c.name FROM customers c
JOIN orders o ON o.customer_id=c.id
JOIN order_items i ON i.order_id=o.id
JOIN products p ON p.id=i.product_id
WHERE p.category='数码' ORDER BY c.id LIMIT 15""").fetchall()])

print("\n== SQL-L7-01 2024下过单的客户(按id序前15) ==")
print([r[0] for r in conn.execute("""
SELECT DISTINCT c.name FROM customers c
JOIN orders o ON o.customer_id=c.id
WHERE o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'
ORDER BY c.id LIMIT 15""").fetchall()])

print("\n== SQL-L7-02 买过智能手机1号的客户(按id序前15) ==")
print([r[0] for r in conn.execute("""
SELECT DISTINCT c.name FROM customers c
JOIN orders o ON o.customer_id=c.id
JOIN order_items i ON i.order_id=o.id
JOIN products p ON p.id=i.product_id
WHERE p.name='智能手机1号' ORDER BY c.id LIMIT 15""").fetchall()])

print("\n== PY-P3-11 各渠道销售额占比(分母=全部已完成) ==")
rows = conn.execute("""
SELECT channel, ROUND(SUM(quantity*unit_price*(1-discount)),2) v FROM v_sales
WHERE status='completed' GROUP BY channel ORDER BY channel""").fetchall()
tot = sum(r[1] for r in rows)
print(rows, "total", round(tot, 2))
print([(c, round(v*100.0/tot, 2)) for c, v in rows])
