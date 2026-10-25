# -*- coding: utf-8 -*-
"""生成验证数据与分析数据: 电商业务 SQLite 库 shop.db
确定子 seed=42, 覆盖 2023-01-01 ~ 2024-12-31, 含季节性与增长趋势。
"""
import os
import random
import sqlite3
import json

import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "shop.db")
GOLDEN_DIR = os.path.join(BASE, "eval")

random.seed(42)
np.random.seed(42)

REGIONS = {
    "华东": ["上海", "杭州", "南京", "苏州", "宁波"],
    "华北": ["北京", "天津", "石家庄", "太原"],
    "华南": ["广州", "深圳", "厦门", "福州"],
    "西南": ["成都", "重庆", "昆明", "贵阳"],
    "东北": ["沈阳", "大连", "哈尔滨", "长春"],
}
CATEGORIES = {
    "数码": ("智能手机", "无线耳机", "智能手表", "平板电脑", "蓝牙音箱"),
    "家电": ("冰箱", "洗衣机", "空调", "电饭煲", "吸尘器"),
    "服饰": ("羽绒服", "T恤", "牛仔裤", "运动鞋", "连衣裙"),
    "食品": ("坚果礼盒", "咖啡豆", "茶叶", "进口牛奶", "零食大礼包"),
    "美妆": ("精华液", "防晒霜", "口红", "面膜", "香水"),
    "家居": ("台灯", "收纳箱", "床上四件套", "香薰", "花瓶"),
}
PRICE_RANGE = {
    "数码": (199, 8999), "家电": (299, 6999), "服饰": (59, 1299),
    "食品": (19, 399), "美妆": (49, 899), "家居": (29, 699),
}
STATUS_W = ["completed"] * 85 + ["cancelled"] * 8 + ["pending"] * 7
MONTH_SEASON = {1: 0.8, 2: 0.6, 3: 0.9, 4: 0.95, 5: 1.0, 6: 1.0,
                7: 0.95, 8: 1.0, 9: 1.05, 10: 1.1, 11: 1.5, 12: 1.4}


def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE customers(
        id INTEGER PRIMARY KEY, name TEXT, city TEXT, region TEXT,
        signup_date TEXT, vip_level INTEGER);
    CREATE TABLE products(
        id INTEGER PRIMARY KEY, name TEXT, category TEXT,
        price REAL, cost REAL);
    CREATE TABLE orders(
        id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT,
        status TEXT, channel TEXT);
    CREATE TABLE order_items(
        id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER,
        quantity INTEGER, unit_price REAL, discount REAL);
    """)
    conn.commit()

    # customers 500
    cities = [(c, r) for r, cs in REGIONS.items() for c in cs]
    cust_rows = []
    for i in range(1, 501):
        city, region = random.choice(cities)
        sd = pd.Timestamp("2022-01-01") + pd.Timedelta(days=random.randint(0, 730))
        cust_rows.append((i, f"用户{i:04d}", city, region, sd.strftime("%Y-%m-%d"), random.randint(0, 3)))
    cur.executemany("INSERT INTO customers VALUES(?,?,?,?,?,?)", cust_rows)

    # products 100
    prod_rows, pid = [], 0
    for cat, names in CATEGORIES.items():
        lo, hi = PRICE_RANGE[cat]
        for j, nm in enumerate(names):
            for k in range(4):  # 每类 20 个商品
                pid += 1
                price = round(random.uniform(lo, hi), 1)
                prod_rows.append((pid, f"{nm}{k+1}号", cat, price, round(price * random.uniform(0.55, 0.8), 1)))
    cur.executemany("INSERT INTO products VALUES(?,?,?,?,?)", prod_rows)

    # orders: 2023/2024 两年, 增长趋势+季节性, 共约 18000
    n2023, n2024 = 7000, 9000
    channels = ["app", "web", "mini_program"]
    order_rows, item_rows = [], []
    oid, iid = 0, 0
    for year, n_total, base in ((2023, n2023, 0.75), (2024, n2024, 1.0)):
        # 按月份季节性分配订单量
        weights = np.array([MONTH_SEASON[m] for m in range(1, 13)])
        month_counts = (weights / weights.sum() * n_total).astype(int)
        for m, cnt in enumerate(month_counts, start=1):
            days_in_month = (pd.Timestamp(year, m + 1, 1) - pd.Timestamp(year, m, 1)).days if m < 12 else 31
            for _ in range(cnt):
                oid += 1
                d = pd.Timestamp(year, m, 1) + pd.Timedelta(days=random.randint(0, days_in_month - 1),
                                                            hours=random.randint(0, 23), minutes=random.randint(0, 59))
                cid = random.randint(1, 500)
                status = random.choice(STATUS_W)
                order_rows.append((oid, cid, d.strftime("%Y-%m-%d %H:%M:%S"), status, random.choice(channels)))
                if status == "cancelled":
                    continue
                for _ in range(random.randint(1, 5)):
                    iid += 1
                    pr = prod_rows[random.randint(0, len(prod_rows) - 1)]
                    qty = random.randint(1, 5)
                    unit_price = round(pr[3] * random.uniform(0.9, 1.0), 2)
                    item_rows.append((iid, oid, pr[0], qty, unit_price, round(random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2]), 2)))

    cur.executemany("INSERT INTO customers VALUES(?,?,?,?,?,?)", []) if False else None
    cur.executemany("INSERT INTO orders VALUES(?,?,?,?,?)", order_rows)
    cur.executemany("INSERT INTO order_items VALUES(?,?,?,?,?,?)", item_rows)
    conn.commit()

    # 索引, 便于查询
    cur.executescript("""
    CREATE INDEX idx_orders_customer ON orders(customer_id);
    CREATE INDEX idx_orders_date ON orders(order_date);
    CREATE INDEX idx_items_order ON order_items(order_id);
    CREATE INDEX idx_items_product ON order_items(product_id);
    """)
    conn.commit()

    stats = {}
    for t in ("customers", "products", "orders", "order_items"):
        stats[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    conn.close()
    print("generated:", json.dumps(stats, ensure_ascii=False))
    return stats


if __name__ == "__main__":
    build()
