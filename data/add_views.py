# -*- coding: utf-8 -*-
"""为小模型构建宽表视图: 消除JOIN错误, 单表即可回答绝大多数分析问题"""
import os
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "shop.db")

VIEWS = """
DROP VIEW IF EXISTS v_sales;
CREATE VIEW v_sales AS
SELECT
    o.id            AS order_id,
    o.order_date    AS order_date,
    substr(o.order_date,1,10) AS order_day,
    substr(o.order_date,1,7)  AS order_month,
    substr(o.order_date,1,4)  AS order_year,
    substr(o.order_date,1,10) AS day,
    substr(o.order_date,1,7)  AS month,
    substr(o.order_date,1,4)  AS year,
    o.status        AS status,
    o.channel       AS channel,
    c.id            AS customer_id,
    c.name          AS customer_name,
    c.city          AS city,
    c.region        AS region,
    c.vip_level     AS vip_level,
    p.id            AS product_id,
    p.name          AS product_name,
    p.category      AS category,
    p.price         AS price,
    i.quantity      AS quantity,
    i.unit_price    AS unit_price,
    i.discount      AS discount,
    ROUND(i.quantity*i.unit_price*(1-i.discount),4) AS amount
FROM orders o
JOIN customers c ON c.id=o.customer_id
LEFT JOIN order_items i ON i.order_id=o.id
LEFT JOIN products p ON p.id=i.product_id;
"""

if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    conn.executescript(VIEWS)
    n = conn.execute("SELECT COUNT(*) FROM v_sales").fetchone()[0]
    conn.close()
    print("v_sales rows:", n)
