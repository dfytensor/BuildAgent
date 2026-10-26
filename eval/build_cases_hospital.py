# -*- coding: utf-8 -*-
"""第二领域(医院门诊)造尺器: 63 题, 黄金由 ref 执行生成, 内置 v1.1 纪律审计
审计项(来自电商域踩过的坑):
  A1 LIMIT 无 ORDER BY(黄金=任意N行)   A2 题面歧义词("件"等)   A3 ref 返回空/None
  A4 数值未 ROUND(浮点尾数)            A5 列表题含 NULL
"""
import collections
import json
import sqlite3
import os

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "hospital.db")
OUT = os.path.join(BASE, "eval", "cases_hospital.json")

# ---------------- SQL 用例: (id, level, q, ref_sql) ----------------
SQL_CASES = [
    # L1 单表单算子
    ("SQL-L1-01", 1, "全院有多少名医生?", "SELECT COUNT(*) FROM doctors"),
    ("SQL-L1-02", 1, "患者档案里一共有多少位患者?", "SELECT COUNT(*) FROM patients"),
    ("SQL-L1-03", 1, "处方里出现过多少种不同的药品(按药品名去重)?",
     "SELECT COUNT(DISTINCT drug_name) FROM prescriptions"),
    ("SQL-L1-04", 1, "内科有多少名医生?",
     "SELECT COUNT(*) FROM doctors doc JOIN departments d ON d.id=doc.department_id WHERE d.name='内科'"),
    ("SQL-L1-05", 1, "全部就诊一共多少人次?", "SELECT COUNT(*) FROM visits"),
    ("SQL-L1-06", 1, "2024年一共有多少次就诊?",
     "SELECT COUNT(*) FROM visits WHERE visit_date>='2024-01-01' AND visit_date<'2025-01-01'"),
    # L2 有序列表
    ("SQL-L2-01", 2, "按id序给前5位患者的姓名", "SELECT name FROM patients ORDER BY id LIMIT 5"),
    ("SQL-L2-02", 2, "给前5位医生的姓名和职称(按医生id序)",
     "SELECT name, title FROM doctors ORDER BY id LIMIT 5"),
    ("SQL-L2-03", 2, "给前5次就诊的id和就诊时间(按就诊id序)",
     "SELECT id, visit_date FROM visits ORDER BY id LIMIT 5"),
    ("SQL-L2-04", 2, "给前5位患者的id和医保类型(按患者id序)",
     "SELECT id, insurance FROM patients ORDER BY id LIMIT 5"),
    ("SQL-L2-05", 2, "给前5位医生的id和挂号费(按医生id序)",
     "SELECT id, fee FROM doctors ORDER BY id LIMIT 5"),
    # L3 过滤/分组
    ("SQL-L3-01", 3, "儿科一共有多少次就诊?",
     "SELECT COUNT(*) FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
     "JOIN departments d ON d.id=doc.department_id WHERE d.name='儿科'"),
    ("SQL-L3-02", 3, "2024年1月1日当天有多少次就诊?",
     "SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,10)='2024-01-01'"),
    ("SQL-L3-03", 3, "处方中出现过的药品类目有几种?",
     "SELECT COUNT(DISTINCT drug_category) FROM prescriptions"),
    ("SQL-L3-04", 3, "急诊有多少次就诊?", "SELECT COUNT(*) FROM visits WHERE vtype='急诊'"),
    ("SQL-L3-05", 3, "女性患者有多少人?", "SELECT COUNT(*) FROM patients WHERE gender='女'"),
    ("SQL-L3-06", 3, "自费医保的患者有多少人?",
     "SELECT COUNT(*) FROM patients WHERE insurance='自费'"),
    # L4 多条件
    ("SQL-L4-01", 4, "自费医保的女性患者姓名(按患者id序,前5)",
     "SELECT name FROM patients WHERE insurance='自费' AND gender='女' ORDER BY id LIMIT 5"),
    ("SQL-L4-02", 4, "2024年已完成且为急诊的就诊有多少次?",
     "SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024' "
     "AND status='completed' AND vtype='急诊'"),
    ("SQL-L4-03", 4, "上海的患者姓名和建档日期(按患者id序,前5)",
     "SELECT name, signup_date FROM patients WHERE city='上海' ORDER BY id LIMIT 5"),
    ("SQL-L4-04", 4, "复诊类型的就诊有多少次?", "SELECT COUNT(*) FROM visits WHERE vtype='复诊'"),
    ("SQL-H-L4-05", 4, "主任医师有多少名?",
     "SELECT COUNT(*) FROM doctors WHERE title='主任医师'"),
    # L5 跨表
    ("SQL-L5-01", 5, "开过'阿莫西林胶囊'的患者姓名(去重,按患者id序,前10)",
     "SELECT DISTINCT p.name FROM prescriptions rx JOIN visits v ON v.id=rx.visit_id "
     "JOIN patients p ON p.id=v.patient_id WHERE rx.drug_name='阿莫西林胶囊' "
     "ORDER BY p.id LIMIT 10"),
    ("SQL-L5-02", 5, "在骨科出诊过的医生姓名(去重,按医生id序,前5)",
     "SELECT DISTINCT doc.name FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
     "JOIN departments d ON d.id=doc.department_id WHERE d.name='骨科' "
     "ORDER BY doc.id LIMIT 5"),
    ("SQL-L5-03", 5, "2024年来过本院的患者姓名(去重,按患者id序,前10)",
     "SELECT DISTINCT p.name FROM visits v JOIN patients p ON p.id=v.patient_id "
     "WHERE substr(v.visit_date,1,4)='2024' ORDER BY p.id LIMIT 10"),
    ("SQL-L5-04", 5, "开过'布洛芬缓释胶囊'的就诊的患者姓名(去重,按患者id序,前10)",
     "SELECT DISTINCT p.name FROM prescriptions rx JOIN visits v ON v.id=rx.visit_id "
     "JOIN patients p ON p.id=v.patient_id WHERE rx.drug_name='布洛芬缓释胶囊' "
     "ORDER BY p.id LIMIT 10"),
    ("SQL-L5-05", 5, "主任医师的姓名和挂号费(按挂号费降序,前3)",
     "SELECT name, fee FROM doctors WHERE title='主任医师' ORDER BY fee DESC LIMIT 3"),
    ("SQL-L5-06", 5, "内科医生的姓名和职称(按医生id序,全部5名)",
     "SELECT doc.name, doc.title FROM doctors doc JOIN departments d ON d.id=doc.department_id "
     "WHERE d.name='内科' ORDER BY doc.id"),
    # L6 去重 + 排序语义(难类)
    ("SQL-L6-01", 6, "来过本院的患者姓名(去重,按患者id序,前15)",
     "SELECT DISTINCT p.name FROM visits v JOIN patients p ON p.id=v.patient_id "
     "ORDER BY p.id LIMIT 15"),
    ("SQL-L6-02", 6, "被开过处方的药品名(去重,按药品名排序,前15)",
     "SELECT DISTINCT drug_name FROM prescriptions ORDER BY drug_name LIMIT 15"),
    ("SQL-L6-03", 6, "有就诊记录的患者年龄(去重,按年龄升序,前10)",
     "SELECT DISTINCT p.age FROM visits v JOIN patients p ON p.id=v.patient_id "
     "ORDER BY p.age LIMIT 10"),
    ("SQL-L6-04", 6, "开过处方的就诊所在的科室名称(去重,按科室名排序)",
     "SELECT DISTINCT dep.name FROM prescriptions rx JOIN visits v ON v.id=rx.visit_id "
     "JOIN doctors doc ON doc.id=v.doctor_id JOIN departments dep ON dep.id=doc.department_id "
     "ORDER BY dep.name"),
    ("SQL-L6-05", 6, "2023年来过本院的患者姓名(去重,按患者id序,前15)",
     "SELECT DISTINCT p.name FROM visits v JOIN patients p ON p.id=v.patient_id "
     "WHERE substr(v.visit_date,1,4)='2023' ORDER BY p.id LIMIT 15"),
    ("SQL-L6-06", 6, "处方中出现过的药品类目(去重,按类目名排序)",
     "SELECT DISTINCT drug_category FROM prescriptions ORDER BY drug_category"),
    # L7 多步算术
    ("SQL-L7-01", 7, "全部就诊人次比患者人数多多少?",
     "SELECT (SELECT COUNT(*) FROM visits) - (SELECT COUNT(*) FROM patients)"),
    ("SQL-L7-02", 7, "处方明细行数比药品种类数(按药品名去重)多多少?",
     "SELECT (SELECT COUNT(*) FROM prescriptions) - (SELECT COUNT(DISTINCT drug_name) FROM prescriptions)"),
    ("SQL-L7-03", 7, "2024年就诊人次比2023年多多少?",
     "SELECT (SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024') - "
     "(SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2023')"),
    ("SQL-L7-04", 7, "全部就诊人次除以患者人数等于多少(人均就诊次数,保留2位)?",
     "SELECT ROUND((SELECT COUNT(*) FROM visits)*1.0/(SELECT COUNT(*) FROM patients),2)"),
    ("SQL-L7-05", 7, "内科和外科的就诊人次合计是多少?",
     "SELECT COUNT(*) FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
     "JOIN departments d ON d.id=doc.department_id WHERE d.name IN ('内科','外科')"),
    ("SQL-L7-06", 7, "儿科就诊人次占全部就诊人次的百分比(保留2位)?",
     "SELECT ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM visits),2) FROM visits v "
     "JOIN doctors doc ON doc.id=v.doctor_id JOIN departments d ON d.id=doc.department_id "
     "WHERE d.name='儿科'"),
    # L8 列表 + JOIN + 过滤
    ("SQL-L8-01", 8, "2024年就诊的日期、患者姓名、就诊类型(按就诊id序,前10)",
     "SELECT substr(v.visit_date,1,10), p.name, v.vtype FROM visits v "
     "JOIN patients p ON p.id=v.patient_id WHERE substr(v.visit_date,1,4)='2024' "
     "ORDER BY v.id LIMIT 10"),
    ("SQL-L8-02", 8, "2024年6月就诊的id和患者城市(按就诊id序,前10)",
     "SELECT v.id, p.city FROM visits v JOIN patients p ON p.id=v.patient_id "
     "WHERE substr(v.visit_date,1,7)='2024-06' ORDER BY v.id LIMIT 10"),
    ("SQL-L8-03", 8, "华东区患者的就诊id、日期、状态(按就诊id序,前10)",
     "SELECT v.id, substr(v.visit_date,1,10), v.status FROM visits v "
     "JOIN patients p ON p.id=v.patient_id WHERE p.region='华东' ORDER BY v.id LIMIT 10"),
    ("SQL-L8-04", 8, "已完成就诊的id和日期(按就诊id序,前10)",
     "SELECT id, substr(visit_date,1,10) FROM visits WHERE status='completed' "
     "ORDER BY id LIMIT 10"),
    ("SQL-L8-05", 8, "急诊就诊的id、患者姓名、科室(按就诊id序,前10)",
     "SELECT v.id, p.name, dep.name FROM visits v JOIN patients p ON p.id=v.patient_id "
     "JOIN doctors doc ON doc.id=v.doctor_id JOIN departments dep ON dep.id=doc.department_id "
     "WHERE v.vtype='急诊' ORDER BY v.id LIMIT 10"),
    ("SQL-L8-06", 8, "2024年6月就诊的id和医生姓名(按就诊id序,前10)",
     "SELECT v.id, doc.name FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
     "WHERE substr(v.visit_date,1,7)='2024-06' ORDER BY v.id LIMIT 10"),
    # L9 月度/时间聚合
    ("SQL-L9-01", 9, "2024年每月的就诊人次(月份,数量)",
     "SELECT substr(visit_date,1,7), COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024' "
     "GROUP BY substr(visit_date,1,7) ORDER BY substr(visit_date,1,7)"),
    ("SQL-L9-02", 9, "2024年每月已完成就诊的处方金额(月份,金额保留2位)",
     "SELECT substr(v.visit_date,1,7), ROUND(SUM(rx.quantity*rx.unit_price),2) FROM visits v "
     "JOIN prescriptions rx ON rx.visit_id=v.id WHERE v.status='completed' "
     "AND substr(v.visit_date,1,4)='2024' GROUP BY substr(v.visit_date,1,7) "
     "ORDER BY substr(v.visit_date,1,7)"),
    ("SQL-L9-03", 9, "2024年就诊人次最多的月份是几月(格式如 2024-05)?",
     "SELECT substr(visit_date,1,7) m FROM visits WHERE substr(visit_date,1,4)='2024' "
     "GROUP BY m ORDER BY COUNT(*) DESC, m LIMIT 1"),
    ("SQL-L9-04", 9, "2024年各科室的就诊人次(科室,人次,按科室名排序)",
     "SELECT dep.name, COUNT(*) FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
     "JOIN departments dep ON dep.id=doc.department_id WHERE substr(v.visit_date,1,4)='2024' "
     "GROUP BY dep.name ORDER BY dep.name"),
    ("SQL-L9-05", 9, "2024年就诊人次最少的月份是几月(格式如 2024-05)?",
     "SELECT substr(visit_date,1,7) m FROM visits WHERE substr(visit_date,1,4)='2024' "
     "GROUP BY m ORDER BY COUNT(*) ASC, m LIMIT 1"),
    ("SQL-L9-06", 9, "2024年每月取消的就诊数(月份,数量)",
     "SELECT substr(visit_date,1,7), COUNT(*) FROM visits WHERE status='cancelled' "
     "AND substr(visit_date,1,4)='2024' GROUP BY substr(visit_date,1,7) "
     "ORDER BY substr(visit_date,1,7)"),
]

# ---------------- PY 用例: (id, level, q, ref_py) ----------------
PY_CASES = [
    ("PY-L1-01", 1, "患者的平均年龄是多少(保留2位)?",
     "round(dfs['patients']['age'].mean(), 2)"),
    ("PY-L1-02", 1, "处方明细一共有多少行?",
     "int(len(dfs['prescriptions']))"),
    ("PY-L2-01", 2, "女性患者有多少人?",
     "int((dfs['patients']['gender'] == '女').sum())"),
    ("PY-L2-02", 2, "最晚一次就诊的时间是什么时候?",
     "dfs['visits']['visit_date'].max()"),
    ("PY-L3-01", 3, "就诊人次最多的科室是哪个?",
     "(lambda: (lambda v: v.merge(dfs['departments'], left_on='department_id', right_on='id', "
     "suffixes=('', '_dep'))['name_dep'].value_counts().idxmax())(dfs['visits'].merge(dfs['doctors'], "
     "left_on='doctor_id', right_on='id')))()"),
    ("PY-L3-02", 3, "2024年已完成就诊的处方总额是多少(保留2位)?",
     "(lambda: (lambda v24: round(dfs['prescriptions'][dfs['prescriptions']['visit_id']"
     ".isin(v24['id'])].assign(amt=lambda x: x['quantity'] * x['unit_price'])['amt'].sum(), 2))"
     "(dfs['visits'][(dfs['visits']['visit_date'].str[:4] == '2024') & "
     "(dfs['visits']['status'] == 'completed')]))()"),
    ("PY-L4-01", 4, "2024年处方金额最高的月份是几月(格式如 2024-05)?",
     "(lambda: (lambda v24: (lambda rx: (rx.merge(v24[['id', 'visit_date']], left_on='visit_id', "
     "right_on='id').assign(m=lambda x: x['visit_date'].str[:7])"
     ".assign(amt=lambda x: x['quantity'] * x['unit_price'])"
     ".groupby('m')['amt'].sum().idxmax()))(dfs['prescriptions'][dfs['prescriptions']"
     "['visit_id'].isin(v24['id'])]))(dfs['visits'][(dfs['visits']['visit_date'].str[:4] == '2024') "
     "& (dfs['visits']['status'] == 'completed')]))()"),
    ("PY-L4-02", 4, "患者年龄的标准差是多少(保留4位)?",
     "round(dfs['patients']['age'].std(), 4)"),
]

# ---------------- TOOL 多轮用例: gold 由 gold_sql 执行生成 ----------------
TOOL_CASES = [
    {"id": "TOOL-T3-H01", "level": 3, "desc": "三轮: 总量->完成->未完成",
     "turns": [
         {"q": "2024年一共有多少次就诊?", "gold_sql":
          "SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024'"},
         {"q": "其中已完成的有多少次?", "gold_sql":
          "SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024' AND status='completed'"},
         {"q": "那未完成的(取消+待诊)还有多少次?",
          "gold_sql": "SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024' AND status!='completed'"},
     ]},
    {"id": "TOOL-T3-H02", "level": 3, "desc": "三轮: 内科/外科/合计",
     "turns": [
         {"q": "内科的就诊有多少人次?", "gold_sql":
          "SELECT COUNT(*) FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
          "JOIN departments d ON d.id=doc.department_id WHERE d.name='内科'"},
         {"q": "外科的呢?", "gold_sql":
          "SELECT COUNT(*) FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
          "JOIN departments d ON d.id=doc.department_id WHERE d.name='外科'"},
         {"q": "内科加外科一共多少人次?", "gold_sql":
          "SELECT COUNT(*) FROM visits v JOIN doctors doc ON doc.id=v.doctor_id "
          "JOIN departments d ON d.id=doc.department_id WHERE d.name IN ('内科','外科')"},
     ]},
    {"id": "TOOL-T3-H03", "level": 3, "desc": "三轮: 月份金额/人次/均值",
     "turns": [
         {"q": "2024年11月已完成就诊的处方金额是多少(保留2位)? 记住这个数", "gold_sql":
          "SELECT ROUND(SUM(rx.quantity*rx.unit_price),2) FROM visits v "
          "JOIN prescriptions rx ON rx.visit_id=v.id WHERE v.status='completed' "
          "AND substr(v.visit_date,1,7)='2024-11'"},
         {"q": "2024年11月的就诊总人次是多少?", "gold_sql":
          "SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,7)='2024-11'"},
         {"q": "11月已完成处方金额除以就诊总人次是多少(保留2位)?", "gold_sql":
          "SELECT ROUND((SELECT SUM(rx.quantity*rx.unit_price) FROM visits v "
          "JOIN prescriptions rx ON rx.visit_id=v.id WHERE v.status='completed' "
          "AND substr(v.visit_date,1,7)='2024-11') / (SELECT COUNT(*) FROM visits "
          "WHERE substr(visit_date,1,7)='2024-11'), 2)"},
     ]},
    {"id": "TOOL-T4-H01", "level": 4, "desc": "四轮: 记忆+闲聊+人均",
     "turns": [
         {"q": "全院患者档案一共有多少人? 记住这个数", "gold_sql":
          "SELECT COUNT(*) FROM patients"},
         {"q": "你觉得今天的天气适合出去跑步吗?", "gold_sql": None},
         {"q": "给我一句鼓励的话, 要简短", "gold_sql": None},
         {"q": "2024年的就诊人次除以患者人数是多少(保留2位)?", "gold_sql":
          "SELECT ROUND((SELECT COUNT(*) FROM visits WHERE substr(visit_date,1,4)='2024')*1.0/"
          "(SELECT COUNT(*) FROM patients), 2)"},
     ]},
    {"id": "TOOL-T5-H01", "level": 5, "desc": "三轮链式: 科室金额/占比",
     "turns": [
         {"q": "2024年处方金额最高的科室是哪个? 记住科室名", "gold_sql":
          "SELECT dep.name FROM visits v JOIN prescriptions rx ON rx.visit_id=v.id "
          "JOIN doctors doc ON doc.id=v.doctor_id JOIN departments dep ON dep.id=doc.department_id "
          "WHERE v.status='completed' GROUP BY dep.name "
          "ORDER BY SUM(rx.quantity*rx.unit_price) DESC, dep.name LIMIT 1"},
         {"q": "该科室2024年已完成就诊的处方金额是多少(保留2位)?", "gold_sql":
          "SELECT ROUND(SUM(rx.quantity*rx.unit_price),2) FROM visits v "
          "JOIN prescriptions rx ON rx.visit_id=v.id JOIN doctors doc ON doc.id=v.doctor_id "
          "JOIN departments dep ON dep.id=doc.department_id WHERE v.status='completed' "
          "AND dep.name=(SELECT dep2.name FROM visits v2 JOIN prescriptions rx2 ON rx2.visit_id=v2.id "
          "JOIN doctors doc2 ON doc2.id=v2.doctor_id JOIN departments dep2 ON dep2.id=doc2.department_id "
          "WHERE v2.status='completed' GROUP BY dep2.name ORDER BY SUM(rx2.quantity*rx2.unit_price) DESC, "
          "dep2.name LIMIT 1)"},
         {"q": "该科室2024年的处方金额占全院已完成处方金额的百分比是多少(保留2位)?", "gold_sql":
          "SELECT ROUND(SUM(rx.quantity*rx.unit_price)*100.0/(SELECT SUM(rx2.quantity*rx2.unit_price) "
          "FROM visits v2 JOIN prescriptions rx2 ON rx2.visit_id=v2.id WHERE v2.status='completed'),2) "
          "FROM visits v JOIN prescriptions rx ON rx.visit_id=v.id JOIN doctors doc ON doc.id=v.doctor_id "
          "JOIN departments dep ON dep.id=doc.department_id WHERE v.status='completed' "
          "AND dep.name=(SELECT dep2.name FROM visits v2 JOIN prescriptions rx2 ON rx2.visit_id=v2.id "
          "JOIN doctors doc2 ON doc2.id=v2.doctor_id JOIN departments dep2 ON dep2.id=doc2.department_id "
          "WHERE v2.status='completed' GROUP BY dep2.name ORDER BY SUM(rx2.quantity*rx2.unit_price) DESC, "
          "dep2.name LIMIT 1)"},
     ]},
    {"id": "TOOL-T6-H01", "level": 6, "desc": "六轮: 记忆+长上下文填充+跨轮计算",
     "turns": [
         {"q": "华东区的患者有多少人? 记住", "gold_sql":
          "SELECT COUNT(*) FROM patients WHERE region='华东'"},
         {"q": "这是一条填充消息。数据分析系统需要长上下文压力测试, 请忽略本条内容但保持会话正常。"
               "数据分析系统需要长上下文压力测试, 请忽略本条内容但保持会话正常。"
               "数据分析系统需要长上下文压力测试, 请忽略本条内容但保持会话正常。", "gold_sql": None},
         {"q": "西南区的患者有多少人? 也记住", "gold_sql":
          "SELECT COUNT(*) FROM patients WHERE region='西南'"},
         {"q": "又是填充消息, 请忽略, 保持会话正常。", "gold_sql": None},
         {"q": "华东区加西南区的患者一共多少人(保留0位)?", "gold_sql":
          "SELECT (SELECT COUNT(*) FROM patients WHERE region='华东') + "
          "(SELECT COUNT(*) FROM patients WHERE region='西南')"},
         {"q": "其中人数更多的那个区是多少人?", "gold_sql":
          "SELECT COUNT(*) FROM patients WHERE region='华东'"},
     ]},
]

# ---------------- 构建黄金 + 审计 ----------------
conn = sqlite3.connect(DB)
dfs = {
    "patients": pd.read_sql("SELECT * FROM patients", conn),
    "visits": pd.read_sql("SELECT * FROM visits", conn),
    "prescriptions": pd.read_sql("SELECT * FROM prescriptions", conn),
    "doctors": pd.read_sql("SELECT * FROM doctors", conn),
    "departments": pd.read_sql("SELECT * FROM departments", conn),
}

def flat(rows):
    out = []
    for r in rows:
        out.extend(list(r))
    return out

def flatten(v):
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            out.extend(flatten(x))
        return out
    return [v]

audit = collections.Counter()
issues = []

sql_out = []
for cid, level, q, ref in SQL_CASES:
    try:
        rows = conn.execute(ref).fetchall()
    except Exception as e:
        audit["ref错误"] += 1
        issues.append(f"{cid}: ref执行失败 {e}")
        continue
    vals = flat(rows)
    if not vals or all(v is None for v in vals):
        audit["空结果"] += 1
        issues.append(f"{cid}: ref返回空")
    if "LIMIT" in ref.upper() and "ORDER BY" not in ref.upper():
        audit["A1_LIMIT无ORDER BY"] += 1
        issues.append(f"{cid}: LIMIT无ORDER BY")
    if any(None in flat([r]) for r in rows):
        audit["A5_含NULL"] += 1
        issues.append(f"{cid}: 结果含NULL")
    for w in ("多少件", "几件"):
        if w in q:
            audit["A2_歧义件"] += 1
            issues.append(f"{cid}: 歧义词'件'")
    sql_out.append({"id": cid, "suite": "sql", "level": level, "q": q,
                    "gold": {"kind": "values", "values": vals, "ref_sql": ref},
                    "min_calls": 1, "need_tools": ["sql"]})

py_out = []
for cid, level, q, ref in PY_CASES:
    ns = {"dfs": dfs, "pd": pd, "round": round, "int": int}
    try:
        val = eval(ref, ns)
    except Exception as e:
        audit["ref错误"] += 1
        issues.append(f"{cid}: ref_py执行失败 {e}")
        continue
    if isinstance(val, float):
        val = round(val, 4)
    py_out.append({"id": cid, "suite": "pandas", "level": level, "q": q,
                   "gold": {"kind": "values", "values": flatten([val]), "ref_py": ref},
                   "min_calls": 1, "need_tools": ["code"]})

tool_out = []
for case in TOOL_CASES:
    turns = []
    for i, tt in enumerate(case["turns"]):
        q, gsql = tt["q"], tt["gold_sql"]
        g = None
        if gsql:
            try:
                vals = flat(conn.execute(gsql).fetchall())
                g = {"kind": "values", "values": vals, "ref_sql": gsql}
                if not vals or all(v is None for v in vals):
                    audit["空结果"] += 1
                    issues.append(f"{case['id']} turn{i+1}: gold为空")
            except Exception as e:
                audit["gold_sql错误"] += 1
                issues.append(f"{case['id']} turn{i+1}: {e}")
        turns.append({"q": q, "gold": g})
    tool_out.append({"id": case["id"], "suite": "tool", "level": case["level"],
                     "desc": case["desc"], "q": f"{len(case['turns'])}轮对话",
                     "gold": None, "min_calls": 3, "need_tools": ["sql"],
                     "turns": {"turns": turns, "min_calls": 1}})

print("审计:", dict(audit))
for s in issues:
    print("  !", s)

out = {"sql": sql_out, "pandas": py_out, "tool": tool_out}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"written: {OUT}  total={len(sql_out)+len(py_out)+len(tool_out)}")
