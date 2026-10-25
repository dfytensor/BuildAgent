# -*- coding: utf-8 -*-
"""v11b: 空结果诊断升级
1) PLANNER_SYS 增加 TEXT 列类型知识(year/month/day 必须字符串比较)
2) 空结果重试提示从"表名可能有误"升级为四步诊断清单
"""
import pathlib

p = pathlib.Path(r"agent\v4_sandbox.py")
t = p.read_text(encoding="utf-8")

old = "- 没有YEAR()/MONTH()/NOW()/FORMAT函数; 年月日用 year/month/day 列, 或 substr(order_date,1,4)='2024'"
new = ("- 没有YEAR()/MONTH()/NOW()/FORMAT函数; 年月日用 year/month/day 列, 或 substr(order_date,1,4)='2024'\n"
       "- year/month/day 是 TEXT 列: 必须用字符串比较如 year='2024'; 写成 year=2024(数字)会查不到任何数据")
assert old in t, "dialect line not found"
t = t.replace(old, new)

old2 = 'why = "查询结果为0行, 表名/条件可能有误(应使用v_sales视图)" if result.get("ok") else str(result.get("error"))[:240]'
new2 = ('why = ("查询返回0行。按顺序诊断: ①年份/月份列是TEXT, 必须用字符串如 year=\'2024\', 数字会查不到 ②'
        '先用 SELECT DISTINCT 该列看真实取值 ③过滤条件可能过严, 先去条件看基数 ④是否该用宽表 v_sales/是否需要JOIN") '
        'if result.get("ok") else str(result.get("error"))[:240]')
assert old2 in t, "empty retry line not found"
t = t.replace(old2, new2)

p.write_text(t, encoding="utf-8")
print("v11b patched: TEXT knowledge + empty-result diagnostic checklist")
