# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r"data\shop.db")
q = "SELECT ROUND(AVG(price),2) FROM products WHERE category='数码'"
print("数码 products.price avg:", conn.execute(q).fetchone())
q2 = """SELECT substr(order_date,1,7) m, ROUND(SUM(status='cancelled')*100.0/COUNT(*),2) r
FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01'
GROUP BY m ORDER BY r DESC LIMIT 3"""
print("2024取消率Top3:", conn.execute(q2).fetchall())
