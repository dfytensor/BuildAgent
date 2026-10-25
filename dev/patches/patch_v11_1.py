# -*- coding: utf-8 -*-
"""v1.1 评测修正:
1) PY-P3-11 黄金错(分母带channel过滤->100%) -> 正确占比
2) SQL-L6-04/L7-01/L7-02 ref无ORDER BY -> 按customer id序
3) 题面去歧义: PY-P1-02 / PY-P2-07 / TOOL-T2-03 / PY-P1-04 / TOOL-T5-04
备份: eval/cases.v1.0.bak.json
"""
import json
import shutil

p = r"eval\cases.json"
shutil.copyfile(p, r"eval\cases.v1.0.bak.json")
cases = json.load(open(p, encoding="utf-8"))
cmap = {}
for s, lst in cases.items():
    for c in lst:
        cmap[c["id"]] = c

# 1) ORDER BY 修正的三题
fix = {
    "SQL-L6-04": {
        "ref": "SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id JOIN order_items i ON i.order_id=o.id JOIN products p ON p.id=i.product_id WHERE p.category='数码' ORDER BY c.id LIMIT 15",
        "vals": ["用户0001", "用户0002", "用户0003", "用户0004", "用户0005", "用户0006", "用户0007",
                 "用户0008", "用户0009", "用户0010", "用户0011", "用户0012", "用户0013", "用户0014", "用户0015"],
    },
    "SQL-L7-01": {
        "ref": "SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id WHERE o.order_date>='2024-01-01' AND o.order_date<'2025-01-01' ORDER BY c.id LIMIT 15",
        "vals": ["用户0001", "用户0002", "用户0003", "用户0004", "用户0005", "用户0006", "用户0007",
                 "用户0008", "用户0009", "用户0010", "用户0011", "用户0012", "用户0013", "用户0014", "用户0015"],
    },
    "SQL-L7-02": {
        "ref": "SELECT DISTINCT c.name FROM customers c JOIN orders o ON o.customer_id=c.id JOIN order_items i ON i.order_id=o.id JOIN products p ON p.id=i.product_id WHERE p.name='智能手机1号' ORDER BY c.id LIMIT 15",
        "vals": ["用户0001", "用户0003", "用户0004", "用户0005", "用户0008", "用户0009", "用户0011",
                 "用户0012", "用户0013", "用户0019", "用户0021", "用户0022", "用户0023", "用户0026", "用户0027"],
    },
}
for cid, f in fix.items():
    c = cmap[cid]
    c["gold"]["ref_sql"] = f["ref"]
    c["gold"]["values"] = f["vals"]

# 2) PY-P3-11 黄金修复
c = cmap["PY-P3-11"]
c["gold"]["ref_sql"] = ("SELECT channel, ROUND(SUM(quantity*unit_price*(1-discount))*100.0/"
                        "(SELECT SUM(quantity*unit_price*(1-discount)) FROM v_sales WHERE status='completed'),2) "
                        "FROM v_sales WHERE status='completed' GROUP BY channel ORDER BY channel")
c["gold"]["values"] = ["app", 33.22, "mini_program", 33.00, "web", 33.79]

# 3) 题面去歧义
cmap["PY-P1-02"]["q"] = "商品表(products)中 price 列的平均值是多少"
cmap["PY-P2-07"]["q"] = "平均每笔订单包含几行商品明细(按明细行数, 保留2位)"
cmap["TOOL-T2-03"]["q"] = "数码类和家电类商品一共有多少款"
cmap["PY-P1-04"]["q"] = "order_items 表的 quantity 列总和是多少"
cmap["PY-P2-02"]["q"] = "数码类商品有几款(商品款数)"
cmap["PY-P2-13"]["q"] = "被购买次数最多的商品id是多少(按订单明细行数统计)"
cmap["PY-P3-15"]["q"] = "2024年取消率最高的月份是几月(回答格式如 2024-05)"
cmap["TOOL-T4-03"]["turns"]["turns"][0]["q"] = "数码类商品(products表)的平均售价是多少? 保留2位并记住"
last_turn = cmap["TOOL-T5-04"]["turns"]["turns"][-1]
last_turn["q"] = last_turn["q"].replace("它贡献的销售额是多少", "它贡献的销售额(含已取消订单)是多少")

json.dump(cases, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("v1.1 applied: 3x ORDER BY, 1x gold fix, 5x wording")
print("backup -> eval/cases.v1.0.bak.json")
