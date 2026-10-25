# -*- coding: utf-8 -*-
"""构建 150 个评测用例 + 黄金答案(golden)。
- SQL 阶梯 50 题(L1-L9, 对应 md 中 9 级复杂度)
- pandas 算子阶梯 50 题(P1-P4, 单算子→多算子→多步→出图)
- 工具调用 50 题(T1-T6, 单轮单次→单轮多次→多轮依赖→跨maxlen依赖)
黄金答案用参考实现(SQL 或 pandas)从 shop.db 预计算, 评测时与 agent 答案自动比对。
"""
import os
import json
import sqlite3
import statistics

import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "shop.db")
conn = sqlite3.connect(DB)


def q(sql):
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    return cols, rows


def gsql(sql, kind="values", limit=50):
    """黄金答案: 执行参考 SQL, 取标量值列表"""
    cols, rows = q(sql)
    flat = []
    for r in rows[:limit]:
        flat.extend([v for v in r if v is not None])
    return {"kind": kind, "values": flat, "ref_sql": sql}


def gpy(code):
    """黄金答案: 用 pandas 参考实现计算, 返回标量值列表"""
    dfs = {
        "customers": pd.read_sql("SELECT * FROM customers", conn),
        "products": pd.read_sql("SELECT * FROM products", conn),
        "orders": pd.read_sql("SELECT * FROM orders", conn),
        "order_items": pd.read_sql("SELECT * FROM order_items", conn),
    }
    loc = {"dfs": dfs, "pd": pd, "np": np, "statistics": statistics}
    vals = eval(code, loc)  # 受控: 仅本构建脚本执行
    if isinstance(vals, (list, tuple, np.ndarray, pd.Series)):
        vals = list(vals)
    else:
        vals = [vals]
    out = []
    for v in vals:
        if isinstance(v, (np.integer,)):
            v = int(v)
        elif isinstance(v, (np.floating, float)):
            v = round(float(v), 4)
        elif isinstance(v, (pd.Timestamp,)):
            v = str(v)
        out.append(v)
    return {"kind": "values", "values": out, "ref_py": code}


CASES = {"sql": [], "pandas": [], "tool": []}


def add(suite, cid, level, desc, question, gold, min_calls=1, turns=None, need_tools=("sql",)):
    CASES[suite].append({
        "id": cid, "level": level, "desc": desc, "q": question,
        "gold": gold, "min_calls": min_calls, "need_tools": list(need_tools),
        "turns": turns,  # 多轮用例: [{q, gold}, ...], 最后一轮的 gold 为主判定
    })


S = "SELECT COUNT(*) FROM "

# ============ SQL 50 题 ============
add("sql", "SQL-L1-01", 1, "单表单字段", "列出所有商品类目(不重复)", gsql("SELECT DISTINCT category FROM products"))
add("sql", "SQL-L1-02", 1, "单表单字段", "列出所有城市(客户表,不重复)", gsql("SELECT DISTINCT city FROM customers"))
add("sql", "SQL-L1-03", 1, "单表单字段", "订单渠道有哪几种", gsql("SELECT DISTINCT channel FROM orders"))
add("sql", "SQL-L1-04", 1, "单表单字段", "订单状态有哪几种", gsql("SELECT DISTINCT status FROM orders"))
add("sql", "SQL-L1-05", 1, "单表单字段", "客户表里出现过的 vip_level 有哪些(去重)", gsql("SELECT DISTINCT vip_level FROM customers ORDER BY 1"))
add("sql", "SQL-L1-06", 1, "单表单字段", "随机给5个商品名", gsql("SELECT name FROM products ORDER BY id LIMIT 5"))
add("sql", "SQL-L2-01", 2, "单表多字段", "给前5位客户的姓名和城市", gsql("SELECT name, city FROM customers ORDER BY id LIMIT 5"))
add("sql", "SQL-L2-02", 2, "单表多字段", "给前5件商品的名称和价格", gsql("SELECT name, price FROM products ORDER BY id LIMIT 5"))
add("sql", "SQL-L2-03", 2, "单表多字段", "给前5个订单的id和下单时间", gsql("SELECT id, order_date FROM orders ORDER BY id LIMIT 5"))
add("sql", "SQL-L2-04", 2, "单表多字段", "给前5位客户的id和vip等级", gsql("SELECT id, vip_level FROM customers ORDER BY id LIMIT 5"))
add("sql", "SQL-L2-05", 2, "单表多字段", "给前5件商品的id和成本", gsql("SELECT id, cost FROM products ORDER BY id LIMIT 5"))
add("sql", "SQL-L2-06", 2, "单表多字段", "给前5个订单的id、状态、渠道", gsql("SELECT id, status, channel FROM orders ORDER BY id LIMIT 5"))
add("sql", "SQL-L3-01", 3, "单表1字段1条件", "数码类商品一共有多少件", gsql("SELECT COUNT(*) FROM products WHERE category='数码'"))
add("sql", "SQL-L3-02", 3, "单表1字段1条件", "vip等级为3的客户有多少", gsql("SELECT COUNT(*) FROM customers WHERE vip_level=3"))
add("sql", "SQL-L3-03", 3, "单表1字段1条件", "上海的客户有多少", gsql("SELECT COUNT(*) FROM customers WHERE city='上海'"))
add("sql", "SQL-L3-04", 3, "单表1字段1条件", "已完成(completed)的订单有多少", gsql("SELECT COUNT(*) FROM orders WHERE status='completed'"))
add("sql", "SQL-L3-05", 3, "单表1字段1条件", "价格超过1000元的商品有几件", gsql("SELECT COUNT(*) FROM products WHERE price>1000"))
add("sql", "SQL-L3-06", 3, "单表1字段1条件", "2024年1月1日当天下了多少单", gsql("SELECT COUNT(*) FROM orders WHERE substr(order_date,1,10)='2024-01-01'"))
add("sql", "SQL-L4-01", 4, "单表多字段1条件", "数码类商品的名称和价格", gsql("SELECT name, price FROM products WHERE category='数码' LIMIT 20"))
add("sql", "SQL-L4-02", 4, "单表多字段1条件", "vip3级客户的姓名和城市", gsql("SELECT name, city FROM customers WHERE vip_level=3 LIMIT 20"))
add("sql", "SQL-L4-03", 4, "单表多字段1条件", "上海客户的姓名和注册日期", gsql("SELECT name, signup_date FROM customers WHERE city='上海' LIMIT 20"))
add("sql", "SQL-L4-04", 4, "单表多字段1条件", "单价大于5000的商品名称和类目", gsql("SELECT name, category FROM products WHERE price>5000"))
add("sql", "SQL-L4-05", 4, "单表多字段1条件", "app渠道订单的id和状态(前10个)", gsql("SELECT id, status FROM orders WHERE channel='app' ORDER BY id LIMIT 10"))
add("sql", "SQL-L4-06", 4, "单表多字段1条件", "价格低于50的商品名称和类目", gsql("SELECT name, category FROM products WHERE price<50"))
add("sql", "SQL-L5-01", 5, "单表多字段多条件", "数码类且价格低于2000的商品名和价格", gsql("SELECT name, price FROM products WHERE category='数码' AND price<2000"))
add("sql", "SQL-L5-02", 5, "单表多字段多条件", "华东区vip等级>=2的客户姓名和等级", gsql("SELECT name, vip_level FROM customers WHERE region='华东' AND vip_level>=2 LIMIT 20"))
add("sql", "SQL-L5-03", 5, "单表多字段多条件", "2024年已完成订单的id和日期(前10)", gsql("SELECT id, substr(order_date,1,10) d FROM orders WHERE status='completed' AND order_date>='2024-01-01' AND order_date<'2025-01-01' ORDER BY id LIMIT 10"))
add("sql", "SQL-L5-04", 5, "单表多字段多条件", "服饰类价格在100到500之间的商品名、价格、成本", gsql("SELECT name, price, cost FROM products WHERE category='服饰' AND price BETWEEN 100 AND 500"))
add("sql", "SQL-L5-05", 5, "单表多字段多条件", "上海和北京的客户姓名与城市(前10)", gsql("SELECT name, city FROM customers WHERE city IN ('上海','北京') ORDER BY id LIMIT 10"))
add("sql", "SQL-L5-06", 5, "单表多字段多条件", "app渠道里被取消的订单id和日期(前10)", gsql("SELECT id, substr(order_date,1,10) d FROM orders WHERE channel='app' AND status='cancelled' ORDER BY id LIMIT 10"))
add("sql", "SQL-L6-01", 6, "多表1字段", "下过订单的客户姓名(去重,前15)", gsql("SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id LIMIT 15"))
add("sql", "SQL-L6-02", 6, "多表1字段", "被购买过的商品名(去重,前15)", gsql("SELECT DISTINCT p.name FROM products p JOIN order_items i ON i.product_id=p.id LIMIT 15"))
add("sql", "SQL-L6-03", 6, "多表1字段", "有订单的客户的注册日期(去重,前15)", gsql("SELECT DISTINCT c.signup_date FROM customers c JOIN orders o ON o.customer_id=c.id ORDER BY 1 LIMIT 15"))
add("sql", "SQL-L6-04", 6, "多表1字段", "买过数码类商品的客户姓名(去重,前15)", gsql("SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id JOIN order_items i ON i.order_id=o.id JOIN products p ON p.id=i.product_id WHERE p.category='数码' LIMIT 15"))
add("sql", "SQL-L6-05", 6, "多表1字段", "下过订单的客户所在城市(去重)", gsql("SELECT DISTINCT c.city FROM customers c JOIN orders o ON o.customer_id=c.id"))
add("sql", "SQL-L7-01", 7, "多表1字段1条件", "2024年下过订单的客户姓名(去重,前15)", gsql("SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id WHERE o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' LIMIT 15"))
add("sql", "SQL-L7-02", 7, "多表1字段1条件", "买过'智能手机1号'的客户姓名(前15)", gsql("SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id JOIN order_items i ON i.order_id=o.id JOIN products p ON p.id=i.product_id WHERE p.name='智能手机1号' LIMIT 15"))
add("sql", "SQL-L7-03", 7, "多表1字段1条件", "数码类商品的总购买件数", gsql("SELECT SUM(i.quantity) FROM order_items i JOIN products p ON p.id=i.product_id WHERE p.category='数码'"))
add("sql", "SQL-L7-04", 7, "多表1字段1条件", "2024年注册的客户数(按注册日期)", gsql("SELECT COUNT(*) FROM customers WHERE substr(signup_date,1,4)='2024'"))
add("sql", "SQL-L7-05", 7, "多表1字段1条件", "vip3级客户的订单总数", gsql("SELECT COUNT(*) FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.vip_level=3"))
add("sql", "SQL-L8-01", 8, "多表多字段1条件", "2024年订单的日期、客户姓名、渠道(前10)", gsql("SELECT substr(o.order_date,1,10) d, c.name, o.channel FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.order_date>='2024-01-01' ORDER BY o.id LIMIT 10"))
add("sql", "SQL-L8-02", 8, "多表多字段1条件", "数码类商品的名称、价格和被购买总件数", gsql("SELECT p.name, p.price, SUM(i.quantity) qty FROM products p JOIN order_items i ON i.product_id=p.id WHERE p.category='数码' GROUP BY p.id ORDER BY p.id"))
add("sql", "SQL-L8-03", 8, "多表多字段1条件", "2024年6月订单的id和客户城市(前10)", gsql("SELECT o.id, c.city FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.order_date>='2024-06-01' AND o.order_date<'2024-07-01' ORDER BY o.id LIMIT 10"))
add("sql", "SQL-L8-04", 8, "多表多字段1条件", "华东区客户的订单id、日期、状态(前10)", gsql("SELECT o.id, substr(o.order_date,1,10) d, o.status FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.region='华东' ORDER BY o.id LIMIT 10"))
add("sql", "SQL-L8-05", 8, "多表多字段1条件", "单笔购买数量>=4的订单id、客户姓名、日期(前10)", gsql("SELECT i.order_id, c.name, substr(o.order_date,1,10) d FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE i.quantity>=4 ORDER BY i.id LIMIT 10"))
add("sql", "SQL-L9-01", 9, "多表多字段多条件聚合", "2024年每月的完成订单数(月份,数量)", gsql("SELECT substr(order_date,1,7) m, COUNT(*) FROM orders WHERE status='completed' AND order_date>='2024-01-01' AND order_date<'2025-01-01' GROUP BY 1 ORDER BY 1"))
add("sql", "SQL-L9-02", 9, "多表多字段多条件聚合", "各类目的销售额(仅已完成订单, 类目,金额)", gsql("SELECT p.category, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) amt FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE o.status='completed' GROUP BY 1 ORDER BY 1"))
add("sql", "SQL-L9-03", 9, "多表多字段多条件聚合", "2024年销售额前5的商品名与销售额(已完成)", gsql("SELECT p.name, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) amt FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY p.id ORDER BY amt DESC LIMIT 5"))
add("sql", "SQL-L9-04", 9, "多表多字段多条件聚合", "各区域2024年已完成订单总金额(区域,金额)", gsql("SELECT c.region, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) amt FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY 1 ORDER BY 1"))
add("sql", "SQL-L9-05", 9, "多表多字段多条件聚合", "2024年消费金额前3的客户姓名与消费额(已完成)", gsql("SELECT c.name, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) amt FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY c.id ORDER BY amt DESC LIMIT 3"))

# ============ pandas 50 题 ============
add("pandas", "PY-P1-01", 1, "单算子", "orders表一共有多少行", gpy("len(dfs['orders'])"), need_tools=("code",))
add("pandas", "PY-P1-02", 1, "单算子", "商品的平均价格是多少", gpy("dfs['products']['price'].mean()"), need_tools=("code",))
add("pandas", "PY-P1-03", 1, "单算子", "最高的客户vip等级是多少", gpy("dfs['customers']['vip_level'].max()"), need_tools=("code",))
add("pandas", "PY-P1-04", 1, "单算子", "购买数量quantity列的总和", gpy("int(dfs['order_items']['quantity'].sum())"), need_tools=("code",))
add("pandas", "PY-P1-05", 1, "单算子", "订单状态一共有几种", gpy("dfs['orders']['status'].nunique()"), need_tools=("code",))
add("pandas", "PY-P1-06", 1, "单算子", "商品最低价格是多少", gpy("dfs['products']['price'].min()"), need_tools=("code",))
add("pandas", "PY-P1-07", 1, "单算子", "客户分布在多少个城市", gpy("dfs['customers']['city'].nunique()"), need_tools=("code",))
add("pandas", "PY-P1-08", 1, "单算子", "最早一笔订单的时间", gpy("str(dfs['orders']['order_date'].min())"), need_tools=("code",))
add("pandas", "PY-P1-09", 1, "单算子", "明细表平均单价是多少", gpy("round(dfs['order_items']['unit_price'].mean(),4)"), need_tools=("code",))
add("pandas", "PY-P1-10", 1, "单算子", "商品成本总和是多少", gpy("round(dfs['products']['cost'].sum(),2)"), need_tools=("code",))
add("pandas", "PY-P2-01", 2, "双算子", "已完成的订单有多少笔", gpy("int((dfs['orders']['status']=='completed').sum())"), need_tools=("code",))
add("pandas", "PY-P2-02", 2, "双算子", "数码类商品有几件", gpy("int((dfs['products']['category']=='数码').sum())"), need_tools=("code",))
add("pandas", "PY-P2-03", 2, "双算子", "2024年的订单有多少笔", gpy("int(dfs['orders']['order_date'].str.startswith('2024').sum())"), need_tools=("code",))
add("pandas", "PY-P2-04", 2, "双算子", "最贵的商品叫什么名字", gpy("dfs['products'].loc[dfs['products']['price'].idxmax(),'name']"), need_tools=("code",))
add("pandas", "PY-P2-05", 2, "双算子", "客户数量最多的城市是哪个", gpy("dfs['customers']['city'].value_counts().idxmax()"), need_tools=("code",))
add("pandas", "PY-P2-06", 2, "双算子", "哪个渠道订单最多", gpy("dfs['orders']['channel'].value_counts().idxmax()"), need_tools=("code",))
add("pandas", "PY-P2-07", 2, "双算子", "平均每笔订单包含几件商品(保留2位)", gpy("round(dfs['order_items'].groupby('order_id').size().mean(),2)"), need_tools=("code",))
add("pandas", "PY-P2-08", 2, "双算子", "购买数量的中位数是多少", gpy("float(dfs['order_items']['quantity'].median())"), need_tools=("code",))
add("pandas", "PY-P2-09", 2, "双算子", "数码类商品的最高价格", gpy("dfs['products'][dfs['products']['category']=='数码']['price'].max()"), need_tools=("code",))
add("pandas", "PY-P2-10", 2, "双算子", "2024年6月的订单数", gpy("int(dfs['orders']['order_date'].str.startswith('2024-06').sum())"), need_tools=("code",))
add("pandas", "PY-P2-11", 2, "双算子", "平均折扣是多少(保留4位)", gpy("round(dfs['order_items']['discount'].mean(),4)"), need_tools=("code",))
add("pandas", "PY-P2-12", 2, "双算子", "华东区客户有多少", gpy("int((dfs['customers']['region']=='华东').sum())"), need_tools=("code",))
add("pandas", "PY-P2-13", 2, "双算子", "被买得最多的商品id是多少", gpy("int(dfs['order_items']['product_id'].value_counts().idxmax())"), need_tools=("code",))
add("pandas", "PY-P2-14", 2, "双算子", "订单按时间排序后第100笔订单的id", gpy("int(dfs['orders'].sort_values('order_date').iloc[99]['id'])"), need_tools=("code",))
add("pandas", "PY-P2-15", 2, "双算子", "商品价格的标准差(保留4位)", gpy("round(dfs['products']['price'].std(),4)"), need_tools=("code",))
add("pandas", "PY-P3-01", 3, "多算子", "各个类目分别有多少件商品(类目,数量 按类目排序)", gpy("sorted(zip(dfs['products'].groupby('category').size().index.tolist(), dfs['products'].groupby('category').size().tolist()))"), need_tools=("code",))
add("pandas", "PY-P3-02", 3, "多算子", "各区域的客户数(区域,数量 按区域排序)", gpy("sorted(zip(dfs['customers'].groupby('region').size().index.tolist(), dfs['customers'].groupby('region').size().tolist()))"), need_tools=("code",))
add("pandas", "PY-P3-03", 3, "多算子", "各状态订单数(状态,数量)", gpy("sorted(zip(dfs['orders'].groupby('status').size().index.tolist(), dfs['orders'].groupby('status').size().tolist()))"), need_tools=("code",))
add("pandas", "PY-P3-04", 3, "多算子", "2024年每月订单数(月份,数量)", gpy("sorted(zip(dfs['orders'][dfs['orders']['order_date'].str.startswith('2024')]['order_date'].str[:7].value_counts().index.tolist(), dfs['orders'][dfs['orders']['order_date'].str.startswith('2024')]['order_date'].str[:7].value_counts().tolist()))"), need_tools=("code",))
add("pandas", "PY-P3-05", 3, "多算子", "把明细和商品表关联后,各类目的销售总件数(类目,件数)", gsql("SELECT p.category, SUM(i.quantity) FROM order_items i JOIN products p ON p.id=i.product_id GROUP BY 1 ORDER BY 1"), need_tools=("code",))
add("pandas", "PY-P3-06", 3, "多算子", "各类目销售额(已完成订单, 金额=件数*单价*(1-折扣), 保留2位)", gsql("SELECT p.category, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE o.status='completed' GROUP BY 1 ORDER BY 1"), need_tools=("code",))
add("pandas", "PY-P3-07", 3, "多算子", "2024年消费金额最高的前3个客户的姓名和金额(已完成,保留2位)", gsql("SELECT c.name, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) a FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY c.id ORDER BY a DESC LIMIT 3"), need_tools=("code",))
add("pandas", "PY-P3-08", 3, "多算子", "下单次数最多的前3位客户id和次数", gsql("SELECT customer_id, COUNT(*) n FROM orders GROUP BY customer_id ORDER BY n DESC, customer_id LIMIT 3"), need_tools=("code",))
add("pandas", "PY-P3-09", 3, "多算子", "复购率: 下过2单及以上的客户占全部下单客户的比例(保留4位)", gpy("round((dfs['orders'].groupby('customer_id').size()>=2).sum()/dfs['orders']['customer_id'].nunique(),4)"), need_tools=("code",))
add("pandas", "PY-P3-10", 3, "多算子", "2024年完成订单金额比2023年增长百分之几(保留2位)", gsql("SELECT ROUND((SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01')*100.0/(SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2023-01-01' AND o.order_date<'2024-01-01')-100,2)"), need_tools=("code",))
add("pandas", "PY-P3-11", 3, "多算子", "各渠道销售额占总销售额的百分比(已完成,渠道,百分比保留2位,按渠道排序)", gsql("SELECT channel, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount))*100.0/(SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i2 JOIN orders o2 ON o2.id=i2.order_id WHERE o2.status='completed'),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' GROUP BY 1 ORDER BY 1"), need_tools=("code",))
add("pandas", "PY-P3-12", 3, "多算子", "平均折扣最高的类目是哪个", gpy("dfs['order_items'].merge(dfs['products'], left_on='product_id', right_on='id').groupby('category')['discount'].mean().idxmax()"), need_tools=("code",))
add("pandas", "PY-P3-13", 3, "多算子", "2024年每月销售额(已完成,月份,金额保留2位)", gsql("SELECT substr(o.order_date,1,7) m, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY 1 ORDER BY 1"), need_tools=("code",))
add("pandas", "PY-P3-14", 3, "多算子", "2024年ARPU人均消费(已完成订单总金额/下单人数,保留2位)", gsql("SELECT ROUND((SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01')/(SELECT COUNT(DISTINCT customer_id) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01'),2)"), need_tools=("code",))
add("pandas", "PY-P3-15", 3, "多算子", "2024年取消率最高的月份是几月", gsql("SELECT m FROM (SELECT substr(order_date,1,7) m, SUM(status='cancelled')*1.0/COUNT(*) r FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01' GROUP BY 1) ORDER BY r DESC, m LIMIT 1"), need_tools=("code",))
add("pandas", "PY-P4-01", 4, "出图", "画2024年每月订单数折线图,保存为 chart_01.png", {"kind": "chart", "values": gsql("SELECT substr(order_date,1,7) m, COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01' GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-02", 4, "出图", "画各类目销售额柱状图(已完成订单),保存为 chart_02.png", {"kind": "chart", "values": gsql("SELECT p.category, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE o.status='completed' GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-03", 4, "出图", "画各区域客户数饼图,保存为 chart_03.png", {"kind": "chart", "values": gsql("SELECT region, COUNT(*) FROM customers GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-04", 4, "出图", "画商品价格分布直方图,保存为 chart_04.png", {"kind": "chart", "values": [int(dfs_stats_price())] if False else {"kind": "chart", "values": []}}, need_tools=("code",))
add("pandas", "PY-P4-05", 4, "出图", "画2024年每月销售额柱状图(已完成),保存为 chart_05.png", {"kind": "chart", "values": gsql("SELECT substr(o.order_date,1,7) m, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-06", 4, "出图", "画各渠道订单数条形图,保存为 chart_06.png", {"kind": "chart", "values": gsql("SELECT channel, COUNT(*) FROM orders GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-07", 4, "出图", "画数码类商品价格条形图,保存为 chart_07.png", {"kind": "chart", "values": gsql("SELECT name, price FROM products WHERE category='数码' ORDER BY id")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-08", 4, "出图", "画2023与2024各季度销售额对比柱状图(已完成),保存为 chart_08.png", {"kind": "chart", "values": gsql("SELECT substr(o.order_date,1,4)||'-Q'||((CAST(substr(o.order_date,6,2) AS INT)-1)/3+1) q, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-09", 4, "出图", "画订单状态占比饼图,保存为 chart_09.png", {"kind": "chart", "values": gsql("SELECT status, COUNT(*) FROM orders GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))
add("pandas", "PY-P4-10", 4, "出图", "画vip等级分布柱状图,保存为 chart_10.png", {"kind": "chart", "values": gsql("SELECT vip_level, COUNT(*) FROM customers GROUP BY 1 ORDER BY 1")["values"]}, need_tools=("code",))


def dfs_stats_price():
    return 0


# ============ tool 50 题 ============
# T1 一轮一次tool (10)
add("tool", "TOOL-T1-01", 1, "一轮一次", "customers表有多少行", gsql(S + "customers"), min_calls=1)
add("tool", "TOOL-T1-02", 1, "一轮一次", "orders表有多少行", gsql(S + "orders"), min_calls=1)
add("tool", "TOOL-T1-03", 1, "一轮一次", "products表有多少行", gsql(S + "products"), min_calls=1)
add("tool", "TOOL-T1-04", 1, "一轮一次", "order_items表有多少行", gsql(S + "order_items"), min_calls=1)
add("tool", "TOOL-T1-05", 1, "一轮一次", "客户0001(名字是'用户0001')的城市和vip等级", gsql("SELECT city, vip_level FROM customers WHERE name='用户0001'"), min_calls=1)
add("tool", "TOOL-T1-06", 1, "一轮一次", "商品'平板电脑1号'的价格", gsql("SELECT price FROM products WHERE name='平板电脑1号'"), min_calls=1)
add("tool", "TOOL-T1-07", 1, "一轮一次", "订单id为1000的状态和渠道", gsql("SELECT status, channel FROM orders WHERE id=1000"), min_calls=1)
add("tool", "TOOL-T1-08", 1, "一轮一次", "华北区有多少客户", gsql("SELECT COUNT(*) FROM customers WHERE region='华北'"), min_calls=1)
add("tool", "TOOL-T1-09", 1, "一轮一次", "美妆类有多少商品", gsql("SELECT COUNT(*) FROM products WHERE category='美妆'"), min_calls=1)
add("tool", "TOOL-T1-10", 1, "一轮一次", "2023年12月有多少订单", gsql("SELECT COUNT(*) FROM orders WHERE order_date>='2023-12-01' AND order_date<'2024-01-01'"), min_calls=1)
# T2 一轮多次tool (10)
add("tool", "TOOL-T2-01", 2, "一轮多次", "customers和orders两个表哪个行数多? 多多少行", gsql("SELECT (SELECT COUNT(*) FROM orders)-(SELECT COUNT(*) FROM customers)"), min_calls=2)
add("tool", "TOOL-T2-02", 2, "一轮多次", "order_items比products多多少行", gsql("SELECT (SELECT COUNT(*) FROM order_items)-(SELECT COUNT(*) FROM products)"), min_calls=2)
add("tool", "TOOL-T2-03", 2, "一轮多次", "数码类和家电类商品加起来一共多少件", gsql("SELECT (SELECT COUNT(*) FROM products WHERE category='数码')+(SELECT COUNT(*) FROM products WHERE category='家电')"), min_calls=2)
add("tool", "TOOL-T2-04", 2, "一轮多次", "最贵商品和最便宜商品的价格差是多少", gsql("SELECT MAX(price)-MIN(price) FROM products"), min_calls=2)
add("tool", "TOOL-T2-05", 2, "一轮多次", "上海和北京的客户加起来一共多少", gsql("SELECT (SELECT COUNT(*) FROM customers WHERE city='上海')+(SELECT COUNT(*) FROM customers WHERE city='北京')"), min_calls=2)
add("tool", "TOOL-T2-06", 2, "一轮多次", "2023年订单数加上2024年订单数一共是多少", gsql("SELECT (SELECT COUNT(*) FROM orders WHERE order_date>='2023-01-01' AND order_date<'2024-01-01')+(SELECT COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01')"), min_calls=2)
add("tool", "TOOL-T2-07", 2, "一轮多次", "订单数最多的客户id是多少? 这位客户在哪个城市", gsql("SELECT c.city FROM (SELECT customer_id, COUNT(*) n FROM orders GROUP BY customer_id ORDER BY n DESC, customer_id LIMIT 1) t JOIN customers c ON c.id=t.customer_id"), min_calls=2)
add("tool", "TOOL-T2-08", 2, "一轮多次", "价格最高的商品属于哪个类目? 该类目一共有多少件商品", gsql("SELECT (SELECT category FROM products ORDER BY price DESC LIMIT 1) cat, (SELECT COUNT(*) FROM products WHERE category=(SELECT category FROM products ORDER BY price DESC LIMIT 1))"), min_calls=2)
add("tool", "TOOL-T2-09", 2, "一轮多次", "已完成和已取消的订单分别有多少笔", gsql("SELECT (SELECT COUNT(*) FROM orders WHERE status='completed'), (SELECT COUNT(*) FROM orders WHERE status='cancelled')"), min_calls=2)
add("tool", "TOOL-T2-10", 2, "一轮多次", "买过'智能手机1号'和买过'冰箱1号'的客户分别有多少", gsql("SELECT (SELECT COUNT(DISTINCT o.customer_id) FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE p.name='智能手机1号'), (SELECT COUNT(DISTINCT o.customer_id) FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE p.name='冰箱1号')"), min_calls=2)


def multi_turn(turns, min_calls=1):
    return {"turns": turns, "min_calls": min_calls}


# T3 多轮每轮一次 (8)
add("tool", "TOOL-T3-01", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "2024年一共有多少笔订单?", "gold": gsql("SELECT COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01'")},
    {"q": "2024年已完成的订单有多少笔?", "gold": gsql("SELECT COUNT(*) FROM orders WHERE status='completed' AND order_date>='2024-01-01' AND order_date<'2025-01-01'")},
    {"q": "那2024年未完成的订单(取消+待处理)还有多少笔?", "gold": gsql("SELECT COUNT(*) FROM orders WHERE status!='completed' AND order_date>='2024-01-01' AND order_date<'2025-01-01'")},
]))
add("tool", "TOOL-T3-02", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "平台一共有多少注册客户?", "gold": gsql(S + "customers")},
    {"q": "一共产生了多少笔订单?", "gold": gsql(S + "orders")},
    {"q": "平均每位客户下几单? 保留2位小数", "gold": {"kind": "values", "values": [round(q(S + "orders")[1][0][0] / q(S + "customers")[1][0][0], 2)]}},
]))
add("tool", "TOOL-T3-03", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "数码类商品有多少件?", "gold": gsql("SELECT COUNT(*) FROM products WHERE category='数码'")},
    {"q": "数码类商品的平均价格是多少? 保留2位", "gold": gsql("SELECT ROUND(AVG(price),2) FROM products WHERE category='数码'")},
    {"q": "买空全部数码类商品(各买一件按平均价)需要多少钱? 保留2位", "gold": {"kind": "values", "values": [round(q("SELECT COUNT(*) FROM products WHERE category='数码'")[1][0][0] * q("SELECT AVG(price) FROM products WHERE category='数码'")[1][0][0], 2)]}},
]))
add("tool", "TOOL-T3-04", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "2024年已完成订单的总销售额是多少? 保留2位", "gold": gsql("SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'")},
    {"q": "2023年同口径销售额是多少? 保留2位", "gold": gsql("SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2023-01-01' AND o.order_date<'2024-01-01'")},
    {"q": "2024年比2023年增长百分之多少? 保留2位", "gold": gsql("SELECT ROUND((SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01')*100.0/(SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2023-01-01' AND o.order_date<'2024-01-01')-100,2)")},
]))
add("tool", "TOOL-T3-05", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "最贵的商品是什么? 多少钱", "gold": gsql("SELECT name, price FROM products ORDER BY price DESC LIMIT 1")},
    {"q": "它被买过多少件?", "gold": gsql("SELECT COALESCE(SUM(i.quantity),0) FROM order_items i JOIN products p ON p.id=i.product_id WHERE p.price=(SELECT MAX(price) FROM products)")},
    {"q": "这些销售按它原价算是多少钱? 保留2位", "gold": {"kind": "values", "values": [round(q("SELECT price FROM products ORDER BY price DESC LIMIT 1")[1][0][0] * (q("SELECT COALESCE(SUM(i.quantity),0) FROM order_items i JOIN products p ON p.id=i.product_id WHERE p.price=(SELECT MAX(price) FROM products)")[1][0][0] or 0), 2)]}},
]))
add("tool", "TOOL-T3-06", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "各区域客户数是多少?", "gold": gsql("SELECT region, COUNT(*) FROM customers GROUP BY 1 ORDER BY 1")},
    {"q": "各区域2024年已完成订单总金额是多少? 保留2位", "gold": gsql("SELECT c.region, ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY 1 ORDER BY 1")},
    {"q": "哪个区域人均消费最高? 人均多少(保留2位)? 按该区域客户数算", "gold": gsql("SELECT region, ROUND(amt/n,2) FROM (SELECT c.region, SUM(i.quantity*i.unit_price*(1-i.discount)) amt, COUNT(DISTINCT c.id) n FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY c.region) ORDER BY 2 DESC LIMIT 1")},
]))
add("tool", "TOOL-T3-07", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "app渠道2024年订单有多少笔?", "gold": gsql("SELECT COUNT(*) FROM orders WHERE channel='app' AND order_date>='2024-01-01' AND order_date<'2025-01-01'")},
    {"q": "web渠道2024年订单有多少笔?", "gold": gsql("SELECT COUNT(*) FROM orders WHERE channel='web' AND order_date>='2024-01-01' AND order_date<'2025-01-01'")},
    {"q": "小程序(mini_program)渠道2024年订单有多少笔? 三个渠道合计多少?", "gold": gsql("SELECT (SELECT COUNT(*) FROM orders WHERE channel='mini_program' AND order_date>='2024-01-01' AND order_date<'2025-01-01'), (SELECT COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01')")},
]))
add("tool", "TOOL-T3-08", 3, "多轮每轮一次", "三轮对话", None, min_calls=3, turns=multi_turn([
    {"q": "一共有多少种商品类目?", "gold": gsql("SELECT COUNT(DISTINCT category) FROM products")},
    {"q": "每个类目各有多少件商品?", "gold": gsql("SELECT category, COUNT(*) FROM products GROUP BY 1 ORDER BY 1")},
    {"q": "商品总数是多少?", "gold": gsql(S + "products")},
]))
# T4 相隔几轮引用 (8): 轮1查值A -> 轮2/3填充 -> 轮4引用A
FILLERS = ["你觉得今天天气适合加班吗?", "帮我写一句鼓励自己的话, 要简短", "1+1等于几? 不用查数据库"]
add("tool", "TOOL-T4-01", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "2024年完成了多少笔订单? 记住这个数", "gold": gsql("SELECT COUNT(*) FROM orders WHERE status='completed' AND order_date>='2024-01-01' AND order_date<'2025-01-01'")},
    {"q": FILLERS[0], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[2], "gold": {"kind": "values", "values": []}},
    {"q": "把这个数乘以2是多少?", "gold": {"kind": "values", "values": [q("SELECT COUNT(*) FROM orders WHERE status='completed' AND order_date>='2024-01-01' AND order_date<'2025-01-01'")[1][0][0] * 2]}},
]))
add("tool", "TOOL-T4-02", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "华东区有多少客户? 记住这个数", "gold": gsql("SELECT COUNT(*) FROM customers WHERE region='华东'")},
    {"q": FILLERS[1], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[0], "gold": {"kind": "values", "values": []}},
    {"q": "华东区客户数占全部客户的百分之几? 保留2位", "gold": gsql("SELECT ROUND((SELECT COUNT(*) FROM customers WHERE region='华东')*100.0/(SELECT COUNT(*) FROM customers),2)")},
]))
add("tool", "TOOL-T4-03", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "数码类商品平均价格是多少? 保留2位并记住", "gold": gsql("SELECT ROUND(AVG(price),2) FROM products WHERE category='数码'")},
    {"q": FILLERS[2], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[1], "gold": {"kind": "values", "values": []}},
    {"q": "用刚才那个数除以2, 等于多少? 保留2位", "gold": {"kind": "values", "values": [round(q("SELECT AVG(price) FROM products WHERE category='数码'")[1][0][0] / 2, 2)]}},
]))
add("tool", "TOOL-T4-04", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "2023年订单总数是多少? 记住", "gold": gsql("SELECT COUNT(*) FROM orders WHERE order_date>='2023-01-01' AND order_date<'2024-01-01'")},
    {"q": FILLERS[0], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[2], "gold": {"kind": "values", "values": []}},
    {"q": "2024年订单比2023年多多少笔?", "gold": gsql("SELECT (SELECT COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01')-(SELECT COUNT(*) FROM orders WHERE order_date>='2023-01-01' AND order_date<'2024-01-01')")},
]))
add("tool", "TOOL-T4-05", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "最贵的商品叫什么? 多少钱?", "gold": gsql("SELECT name, price FROM products ORDER BY price DESC LIMIT 1")},
    {"q": FILLERS[1], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[0], "gold": {"kind": "values", "values": []}},
    {"q": "这件商品打8折是多少钱? 保留2位", "gold": {"kind": "values", "values": [round(q("SELECT MAX(price) FROM products")[1][0][0] * 0.8, 2)]}},
]))
add("tool", "TOOL-T4-06", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "上海有多少客户? 记住这个数", "gold": gsql("SELECT COUNT(*) FROM customers WHERE city='上海'")},
    {"q": FILLERS[2], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[1], "gold": {"kind": "values", "values": []}},
    {"q": "再加上北京客户数, 一共是多少?", "gold": gsql("SELECT (SELECT COUNT(*) FROM customers WHERE city='上海')+(SELECT COUNT(*) FROM customers WHERE city='北京')")},
]))
add("tool", "TOOL-T4-07", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "已完成订单的销售额是多少? 保留2位并记住", "gold": gsql("SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed'")},
    {"q": FILLERS[0], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[1], "gold": {"kind": "values", "values": []}},
    {"q": "刚才的销售额除以订单量(取整)是多少?", "gold": gsql("SELECT CAST(SUM(i.quantity*i.unit_price*(1-i.discount))/COUNT(DISTINCT i.order_id) AS INT) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed'")},
]))
add("tool", "TOOL-T4-08", 4, "相隔几轮引用", "四轮对话", None, min_calls=2, turns=multi_turn([
    {"q": "购买数量最大的一笔明细, 数量是多少? 记住", "gold": gsql("SELECT MAX(quantity) FROM order_items")},
    {"q": FILLERS[1], "gold": {"kind": "values", "values": []}},
    {"q": FILLERS[2], "gold": {"kind": "values", "values": []}},
    {"q": "这个数量比平均单笔购买数量多多少? 保留2位", "gold": {"kind": "values", "values": [round(q("SELECT MAX(quantity) FROM order_items")[1][0][0] - q("SELECT AVG(quantity) FROM order_items")[1][0][0], 2)]}},
]))
# T5 连续多跳依赖 (7): 每轮依赖上一轮答案
add("tool", "TOOL-T5-01", 5, "连续多跳", "四轮链式", None, min_calls=4, turns=multi_turn([
    {"q": "金额最大的订单(已完成,金额=件数*单价*(1-折扣))的id是多少?", "gold": gsql("SELECT i.order_id FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' GROUP BY i.order_id ORDER BY SUM(i.quantity*i.unit_price*(1-i.discount)) DESC LIMIT 1")},
    {"q": "这笔订单是谁下的? 告诉我客户姓名", "gold": None},  # 依赖上轮, 动态计算
    {"q": "这位客户在哪个城市?", "gold": None},
    {"q": "这位客户2024年在本平台共消费多少? 保留2位", "gold": None},
]))
add("tool", "TOOL-T5-02", 5, "连续多跳", "四轮链式", None, min_calls=3, turns=multi_turn([
    {"q": "买过最多件商品(按明细件数合计)的客户id是多少?", "gold": gsql("SELECT customer_id FROM orders o JOIN order_items i ON i.order_id=o.id GROUP BY o.customer_id ORDER BY SUM(i.quantity) DESC, o.customer_id LIMIT 1")},
    {"q": "这位客户的城市和vip等级?", "gold": None},
    {"q": "这位客户一共下过多少单?", "gold": None},
]))
add("tool", "TOOL-T5-03", 5, "连续多跳", "四轮链式", None, min_calls=3, turns=multi_turn([
    {"q": "2024年哪个月销售额最高(已完成)? 月份是多少", "gold": gsql("SELECT substr(o.order_date,1,7) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' GROUP BY 1 ORDER BY SUM(i.quantity*i.unit_price*(1-i.discount)) DESC LIMIT 1")},
    {"q": "那个月的订单有多少笔?", "gold": None},
    {"q": "那个月平均每单多少钱(已完成)? 保留2位", "gold": None},
]))
add("tool", "TOOL-T5-04", 5, "连续多跳", "四轮链式", None, min_calls=3, turns=multi_turn([
    {"q": "被购买件数最多的商品id是多少?", "gold": gsql("SELECT product_id FROM order_items GROUP BY product_id ORDER BY SUM(quantity) DESC, product_id LIMIT 1")},
    {"q": "这件商品的名称、类目和单价?", "gold": None},
    {"q": "它贡献的销售额是多少? 保留2位", "gold": None},
]))
add("tool", "TOOL-T5-05", 5, "连续多跳", "四轮链式", None, min_calls=3, turns=multi_turn([
    {"q": "取消订单最多的客户id是多少?", "gold": gsql("SELECT customer_id FROM orders WHERE status='cancelled' GROUP BY customer_id ORDER BY COUNT(*) DESC, customer_id LIMIT 1")},
    {"q": "这位客户的姓名和城市?", "gold": None},
    {"q": "这位客户的订单总数是多少? 其中取消多少笔?", "gold": None},
]))
add("tool", "TOOL-T5-06", 5, "连续多跳", "四轮链式", None, min_calls=3, turns=multi_turn([
    {"q": "平均单价最高的类目是哪个?", "gold": gsql("SELECT category FROM products GROUP BY category ORDER BY AVG(price) DESC LIMIT 1")},
    {"q": "该类目商品的平均价格是多少? 保留2位", "gold": None},
    {"q": "该类目2024年已完成的销售额是多少? 保留2位", "gold": None},
]))
add("tool", "TOOL-T5-07", 5, "连续多跳", "四轮链式", None, min_calls=3, turns=multi_turn([
    {"q": "2024年订单最多的渠道是哪个?", "gold": gsql("SELECT channel FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01' GROUP BY channel ORDER BY COUNT(*) DESC LIMIT 1")},
    {"q": "该渠道2024年已完成订单的金额是多少? 保留2位", "gold": None},
    {"q": "该渠道订单数占2024年总订单的百分比? 保留2位", "gold": None},
]))
# T6 跨maxlen依赖 (7): 填充轮撑大上下文后引用最早值
def long_filler(n):
    return f"这是第{n}条填充消息。" + "数据分析系统需要长上下文压力测试,请忽略本条内容但保持会话正常。" * 6

add("tool", "TOOL-T6-01", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "平台总客户数是多少? 记住它", "gold": gsql(S + "customers")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 5)],
    {"q": "最开始我问的那个数(总客户数)是多少?", "gold": gsql(S + "customers")},
]))
add("tool", "TOOL-T6-02", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "订单表总行数是多少? 记住", "gold": gsql(S + "orders")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 5)],
    {"q": "订单表总行数乘以3是多少?", "gold": {"kind": "values", "values": [q(S + "orders")[1][0][0] * 3]}},
]))
add("tool", "TOOL-T6-03", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "商品总数和类目数分别是多少? 记住", "gold": gsql("SELECT (SELECT COUNT(*) FROM products), (SELECT COUNT(DISTINCT category) FROM products)")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 6)],
    {"q": "商品总数除以类目数(保留2位)等于多少?", "gold": {"kind": "values", "values": [round(q(S + "products")[1][0][0] / q("SELECT COUNT(DISTINCT category) FROM products")[1][0][0], 2)]}},
]))
add("tool", "TOOL-T6-04", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "2024年订单数是多少? 记住", "gold": gsql("SELECT COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01'")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 6)],
    {"q": "还记得最开始问的2024年订单数吗? 顺便告诉我2023年的订单数", "gold": gsql("SELECT COUNT(*) FROM orders WHERE order_date>='2023-01-01' AND order_date<'2024-01-01'")},
]))
add("tool", "TOOL-T6-05", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "华南区客户数是多少? 记住", "gold": gsql("SELECT COUNT(*) FROM customers WHERE region='华南'")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 7)],
    {"q": "华南区客户数加上西南区客户数是多少?", "gold": gsql("SELECT (SELECT COUNT(*) FROM customers WHERE region='华南')+(SELECT COUNT(*) FROM customers WHERE region='西南')")},
]))
add("tool", "TOOL-T6-06", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "2024年已完成销售额是多少? 保留2位并记住", "gold": gsql("SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 7)],
    {"q": "最开始那个2024销售额, 打9折后是多少? 保留2位", "gold": {"kind": "values", "values": [round(q("SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND order_date<'2025-01-01'")[1][0][0] * 0.9, 2)]}},
]))
add("tool", "TOOL-T6-07", 6, "跨maxlen依赖", "多轮长对话", None, min_calls=2, turns=multi_turn([
    {"q": "数码类商品总数是多少? 记住", "gold": gsql("SELECT COUNT(*) FROM products WHERE category='数码'")},
    *[{"q": long_filler(i), "gold": {"kind": "values", "values": []}} for i in range(1, 8)],
    {"q": "第一个问题我问的数码类商品数是多少? 如果记不住请重新查一次", "gold": gsql("SELECT COUNT(*) FROM products WHERE category='数码'")},
]))

# ============ T5/T6 动态黄金答案计算(依赖链式查询结果) ============
def compute_dynamic_goldens():
    for c in CASES["tool"]:
        if not c.get("turns"):
            continue
        prev = {}
        for t in c["turns"]["turns"]:
            if t["gold"] is not None:
                continue
            # 根据前序轮次的黄金查询推导
            vals = []
            g0 = c["turns"]["turns"][0]["gold"]
            v0 = g0["values"][0] if g0 and g0["values"] else None
            tid = c["id"]
            if tid == "TOOL-T5-01":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT c.name FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id={v0}")
                    vals = rows[0]
                elif t is c["turns"]["turns"][2]:
                    cols, rows = q(f"SELECT c.city FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id={v0}")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND c.name=(SELECT c2.name FROM orders o2 JOIN customers c2 ON c2.id=o2.customer_id WHERE o2.id={v0}) AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'")
                    vals = rows[0]
            elif tid == "TOOL-T5-02":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT city, vip_level FROM customers WHERE id={v0}")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT COUNT(*) FROM orders WHERE customer_id={v0}")
                    vals = rows[0]
            elif tid == "TOOL-T5-03":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT COUNT(*) FROM orders WHERE substr(order_date,1,7)='{v0}'")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT ROUND(AVG(amt),2) FROM (SELECT o.id, SUM(i.quantity*i.unit_price*(1-i.discount)) amt FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND substr(o.order_date,1,7)='{v0}' GROUP BY o.id)")
                    vals = rows[0]
            elif tid == "TOOL-T5-04":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT name, category, price FROM products WHERE id={v0}")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT ROUND(SUM(quantity*unit_price*(1-discount)),2) FROM order_items WHERE product_id={v0}")
                    vals = rows[0]
            elif tid == "TOOL-T5-05":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT name, city FROM customers WHERE id={v0}")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT COUNT(*), SUM(status='cancelled') FROM orders WHERE customer_id={v0}")
                    vals = rows[0]
            elif tid == "TOOL-T5-06":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT ROUND(AVG(price),2) FROM products WHERE category='{v0}'")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN products p ON p.id=i.product_id JOIN orders o ON o.id=i.order_id WHERE p.category='{v0}' AND o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'")
                    vals = rows[0]
            elif tid == "TOOL-T5-07":
                if t is c["turns"]["turns"][1]:
                    cols, rows = q(f"SELECT ROUND(SUM(i.quantity*i.unit_price*(1-i.discount)),2) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.channel='{v0}' AND o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'")
                    vals = rows[0]
                else:
                    cols, rows = q(f"SELECT ROUND((SELECT COUNT(*) FROM orders WHERE channel='{v0}' AND order_date>='2024-01-01' AND order_date<'2025-01-01')*100.0/(SELECT COUNT(*) FROM orders WHERE order_date>='2024-01-01' AND order_date<'2025-01-01'),2)")
                    vals = rows[0]
            flat = []
            for r in (rows if 'rows' in dir() else []):
                pass
            for r in vals if isinstance(vals, list) else [vals]:
                flat.append(r)
            t["gold"] = {"kind": "values", "values": flat}


compute_dynamic_goldens()

# 修正 T6-06 的黄金 SQL 笔误重算
for c in CASES["tool"]:
    if c["id"] == "TOOL-T6-06":
        last = c["turns"]["turns"][-1]
        v = q("SELECT SUM(i.quantity*i.unit_price*(1-i.discount)) FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='completed' AND o.order_date>='2024-01-01' AND o.order_date<'2025-01-01'")[1][0][0]
        last["gold"] = {"kind": "values", "values": [round(v * 0.9, 2)]}

# P4-04 商品价格分布直方图黄金: 无具体值要求, 只要求出图
for c in CASES["pandas"]:
    if c["id"] == "PY-P4-04":
        c["gold"] = {"kind": "chart", "values": []}

# ============ 输出 ============
total = sum(len(v) for v in CASES.values())
with open(os.path.join(BASE, "eval", "cases.json"), "w", encoding="utf-8") as f:
    json.dump(CASES, f, ensure_ascii=False, indent=1)
print(f"cases total={total} sql={len(CASES['sql'])} pandas={len(CASES['pandas'])} tool={len(CASES['tool'])}")
# 自检: 所有黄金答案必须非空(kind=chart 除外)
bad = []
for suite, lst in CASES.items():
    for c in lst:
        golds = [c["gold"]] if c["gold"] else []
        if c.get("turns"):
            golds = [t["gold"] for t in c["turns"]["turns"]]
        for g in golds:
            if g is None or (g["kind"] != "chart" and not g["values"] and suite != "tool"):
                bad.append(c["id"])
print("empty-golden cases:", bad if bad else "none")
conn.close()
