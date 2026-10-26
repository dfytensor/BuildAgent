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

-- 订单宽表: 一行 = 一笔订单(含无明细订单), 订单级问题用它, 天然不会重复
DROP VIEW IF EXISTS v_orders;
CREATE VIEW v_orders AS
SELECT o.id AS order_id, o.customer_id, c.name AS customer_name, c.city, c.region, c.vip_level,
       o.order_date,
       substr(o.order_date,1,4) AS year,
       substr(o.order_date,1,7) AS month,
       substr(o.order_date,1,10) AS day,
       o.status, o.channel,
       COUNT(i.id) AS item_lines,
       COALESCE(SUM(i.quantity),0) AS qty,
       ROUND(COALESCE(SUM(i.quantity*i.unit_price*(1-i.discount)),0),2) AS amount
FROM orders o
JOIN customers c ON c.id=o.customer_id
LEFT JOIN order_items i ON i.order_id=o.id
GROUP BY o.id;

-- 客户宽表: 一行 = 一位客户, 客户级统计用它
DROP VIEW IF EXISTS v_customers;
CREATE VIEW v_customers AS
SELECT c.id AS customer_id, c.name AS customer_name, c.city, c.region, c.vip_level, c.signup_date,
       COUNT(DISTINCT o.id) AS order_count,
       COUNT(DISTINCT CASE WHEN o.status='completed' THEN o.id END) AS completed_order_count,
       ROUND(COALESCE(SUM(CASE WHEN o.status='completed' THEN i.quantity*i.unit_price*(1-i.discount) END),0),2) AS completed_amount
FROM customers c
LEFT JOIN orders o ON o.customer_id=c.id
LEFT JOIN order_items i ON i.order_id=o.id
GROUP BY c.id;

-- 商品销售汇总: 一行 = 一个商品, 商品排行用它
DROP VIEW IF EXISTS v_product_sales;
CREATE VIEW v_product_sales AS
SELECT p.id AS product_id, p.name AS product_name, p.category, p.price, p.cost,
       COALESCE(SUM(i.quantity),0) AS qty,
       COUNT(i.id) AS line_count,
       COUNT(DISTINCT i.order_id) AS order_count,
       ROUND(COALESCE(SUM(i.quantity*i.unit_price*(1-i.discount)),0),2) AS amount
FROM products p
LEFT JOIN order_items i ON i.product_id=p.id
GROUP BY p.id;
"""

if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    conn.executescript(VIEWS)
    n = conn.execute("SELECT COUNT(*) FROM v_sales").fetchone()[0]
    conn.close()
    print("v_sales rows:", n)
