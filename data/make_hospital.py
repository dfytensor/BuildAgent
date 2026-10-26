# -*- coding: utf-8 -*-
"""第二领域验证: 医院门诊业务 SQLite 库 hospital.db
确定性 seed=42, 覆盖 2023-01-01 ~ 2024-12-31, 呼吸道疾病季节性(冬高夏低)。
结构同构映射(用于检验方法论跨域迁移):
  visits(就诊) <-> orders   prescriptions(处方明细) <-> order_items
  patients(患者) <-> customers   drugs(药品) <-> products
  insurance(医保类型) <-> channel   无处方就诊 <-> 空明细订单
"""
import os
import random
import sqlite3
import json

import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "hospital.db")

random.seed(42)
np.random.seed(42)

REGIONS = {
    "华东": ["上海", "杭州", "南京", "苏州", "宁波"],
    "华北": ["北京", "天津", "石家庄", "太原"],
    "华南": ["广州", "深圳", "厦门", "福州"],
    "西南": ["成都", "重庆", "昆明", "贵阳"],
    "东北": ["沈阳", "大连", "哈尔滨", "长春"],
}
DEPARTMENTS = ["内科", "外科", "儿科", "骨科", "妇产科", "眼科", "皮肤科", "耳鼻喉科"]
TITLES = ["主任医师", "副主任医师", "主治医师", "住院医师"]
DRUG_CATS = {
    "抗生素": ("阿莫西林胶囊", "头孢克肟片", "阿奇霉素片", "罗红霉素胶囊"),
    "中成药": ("感冒灵颗粒", "板蓝根颗粒", "连花清瘟胶囊", "藿香正气水"),
    "解热镇痛": ("布洛芬缓释胶囊", "对乙酰氨基酚片", "双氯芬酸钠肠溶片", "尼美舒利颗粒"),
    "维生素": ("维生素C片", "维生素D滴剂", "复合维生素B片", "碳酸钙D3片"),
    "慢性病用药": ("二甲双胍片", "硝苯地平缓释片", "阿托伐他汀钙片", "缬沙坦胶囊"),
    "消化用药": ("奥美拉唑肠溶胶囊", "铝碳酸镁咀嚼片", "多潘立酮片", "蒙脱石散"),
}
PRICE_RANGE = {"抗生素": (12, 68), "中成药": (9, 45), "解热镇痛": (8, 39),
               "维生素": (15, 89), "慢性病用药": (18, 96), "消化用药": (10, 62)}
STATUS_W = ["completed"] * 80 + ["cancelled"] * 10 + ["pending"] * 10
VTYPES = ["门诊"] * 70 + ["急诊"] * 18 + ["复诊"] * 12
INSURANCE = ["城镇职工"] * 40 + ["城乡居民"] * 35 + ["自费"] * 25
MONTH_SEASON = {1: 1.45, 2: 1.2, 3: 0.95, 4: 0.85, 5: 0.8, 6: 0.75,
                7: 0.7, 8: 0.72, 9: 0.85, 10: 0.95, 11: 1.25, 12: 1.5}


def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE departments(
        id INTEGER PRIMARY KEY, name TEXT, floor INTEGER);
    CREATE TABLE doctors(
        id INTEGER PRIMARY KEY, name TEXT, department_id INTEGER,
        title TEXT, fee REAL);
    CREATE TABLE patients(
        id INTEGER PRIMARY KEY, name TEXT, gender TEXT, age INTEGER,
        city TEXT, region TEXT, insurance TEXT, signup_date TEXT);
    CREATE TABLE visits(
        id INTEGER PRIMARY KEY, patient_id INTEGER, doctor_id INTEGER,
        visit_date TEXT, status TEXT, vtype TEXT);
    CREATE TABLE prescriptions(
        id INTEGER PRIMARY KEY, visit_id INTEGER, drug_name TEXT,
        drug_category TEXT, quantity INTEGER, unit_price REAL);
    """)
    conn.commit()

    # departments 8
    dept_rows = [(i + 1, name, i + 3) for i, name in enumerate(DEPARTMENTS)]
    cur.executemany("INSERT INTO departments VALUES(?,?,?)", dept_rows)

    # doctors 40 (每科室 5 名)
    doc_rows = []
    did = 0
    for d in range(1, 9):
        for k in range(5):
            did += 1
            title = TITLES[k % 4]
            fee = round(random.uniform(10, 60), 0)
            doc_rows.append((did, f"医生{did:03d}", d, title, fee))
    cur.executemany("INSERT INTO doctors VALUES(?,?,?,?,?)", doc_rows)

    # patients 500
    cities = [(c, r) for r, cs in REGIONS.items() for c in cs]
    pat_rows = []
    for i in range(1, 501):
        city, region = random.choice(cities)
        sd = pd.Timestamp("2022-01-01") + pd.Timedelta(days=random.randint(0, 730))
        pat_rows.append((i, f"患者{i:04d}", random.choice(["男", "女"]),
                         random.randint(1, 88), city, region,
                         random.choice(INSURANCE), sd.strftime("%Y-%m-%d")))
    cur.executemany("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?)", pat_rows)

    # drugs 120
    drug_rows = []
    for cat, names in DRUG_CATS.items():
        lo, hi = PRICE_RANGE[cat]
        for nm in names:
            for k in range(5):
                price = round(random.uniform(lo, hi), 2)
                drug_rows.append((nm, cat, price))
    cur.executemany("INSERT INTO prescriptions(drug_name,drug_category,unit_price) VALUES(?,?,?)",
                    []) if False else None

    # visits: 2023/2024, 呼吸道疾病季节性(冬高夏低), 共约 16000
    n2023, n2024 = 7000, 9000
    visit_rows, rx_rows = [], []
    vid, rid = 0, 0
    drug_pool = [(nm, cat, round(random.uniform(
        PRICE_RANGE[cat][0], PRICE_RANGE[cat][1]), 2)) for nm, cat, _ in drug_rows]
    for year, n_total in ((2023, n2023), (2024, n2024)):
        weights = np.array([MONTH_SEASON[m] for m in range(1, 13)])
        month_counts = (weights / weights.sum() * n_total).astype(int)
        for m, cnt in enumerate(month_counts, start=1):
            days_in_month = (pd.Timestamp(year, m + 1, 1) - pd.Timestamp(year, m, 1)).days if m < 12 else 31
            for _ in range(cnt):
                vid += 1
                d = pd.Timestamp(year, m, 1) + pd.Timedelta(days=random.randint(0, days_in_month - 1),
                                                             hours=random.randint(8, 20), minutes=random.randint(0, 59))
                pid = random.randint(1, 500)
                doc = random.randint(1, 40)
                status = random.choice(STATUS_W)
                visit_rows.append((vid, pid, doc, d.strftime("%Y-%m-%d %H:%M:%S"),
                                   status, random.choice(VTYPES)))
                if status == "cancelled":
                    continue
                # 约 8% 的就诊无处方(纯挂号/开检查单) —— 与空明细订单同构
                if random.random() < 0.08:
                    continue
                for _ in range(random.randint(1, 6)):
                    rid += 1
                    nm, cat, price = drug_pool[random.randint(0, len(drug_pool) - 1)]
                    qty = random.randint(1, 14)
                    rx_rows.append((rid, vid, nm, cat, qty, price))

    cur.executemany("INSERT INTO visits VALUES(?,?,?,?,?,?)", visit_rows)
    cur.executemany("INSERT INTO prescriptions VALUES(?,?,?,?,?,?)", rx_rows)
    conn.commit()

    cur.executescript("""
    CREATE INDEX idx_visits_patient ON visits(patient_id);
    CREATE INDEX idx_visits_date ON visits(visit_date);
    CREATE INDEX idx_visits_doctor ON visits(doctor_id);
    CREATE INDEX idx_rx_visit ON prescriptions(visit_id);
    """)
    conn.commit()

    stats = {}
    for t in ("departments", "doctors", "patients", "visits", "prescriptions"):
        stats[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    conn.close()
    print("generated:", json.dumps(stats, ensure_ascii=False))
    return stats


if __name__ == "__main__":
    build()
