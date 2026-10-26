# -*- coding: utf-8 -*-
"""为医院门诊库构建语义视图(第二领域验证):
结构与电商域严格同构 —— 视图与电商域一一对应:
  v_rx(处方明细宽表,一行=一个处方明细,含无处方就诊的空行) <-> v_sales
  v_visits(就诊宽表,一行=一次就诊)                       <-> v_orders
  v_patients(患者宽表,一行=一位患者)                     <-> v_customers
  v_drugs(药品销售汇总,一行=一个药品)                     <-> v_product_sales
"""
import os
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "hospital.db")

VIEWS = """
DROP VIEW IF EXISTS v_rx;
CREATE VIEW v_rx AS
SELECT
    v.id            AS visit_id,
    v.visit_date    AS visit_date,
    substr(v.visit_date,1,10) AS visit_day,
    substr(v.visit_date,1,7)  AS month,
    substr(v.visit_date,1,4)  AS year,
    v.status        AS status,
    v.vtype         AS vtype,
    p.id            AS patient_id,
    p.name          AS patient_name,
    p.city          AS city,
    p.region        AS region,
    p.insurance     AS insurance,
    doc.id          AS doctor_id,
    doc.name        AS doctor_name,
    doc.title       AS doctor_title,
    dep.name        AS department,
    rx.drug_name    AS drug_name,
    rx.drug_category AS drug_category,
    rx.quantity     AS quantity,
    rx.unit_price   AS unit_price,
    ROUND(rx.quantity*rx.unit_price,2) AS amount
FROM visits v
JOIN patients p ON p.id=v.patient_id
JOIN doctors doc ON doc.id=v.doctor_id
JOIN departments dep ON dep.id=doc.department_id
LEFT JOIN prescriptions rx ON rx.visit_id=v.id;

-- 就诊宽表: 一行 = 一次就诊(含无处方就诊), 就诊级问题用它, 天然不会重复
DROP VIEW IF EXISTS v_visits;
CREATE VIEW v_visits AS
SELECT v.id AS visit_id, v.patient_id, p.name AS patient_name, p.city, p.region,
       p.insurance, v.doctor_id, doc.name AS doctor_name, dep.name AS department,
       doc.title AS doctor_title,
       v.visit_date,
       substr(v.visit_date,1,4) AS year,
       substr(v.visit_date,1,7) AS month,
       substr(v.visit_date,1,10) AS day,
       v.status, v.vtype,
       COUNT(rx.id) AS rx_lines,
       COALESCE(SUM(rx.quantity),0) AS qty,
       ROUND(COALESCE(SUM(rx.quantity*rx.unit_price),0),2) AS amount
FROM visits v
JOIN patients p ON p.id=v.patient_id
JOIN doctors doc ON doc.id=v.doctor_id
JOIN departments dep ON dep.id=doc.department_id
LEFT JOIN prescriptions rx ON rx.visit_id=v.id
GROUP BY v.id;

-- 患者宽表: 一行 = 一位患者, 患者级统计用它
DROP VIEW IF EXISTS v_patients;
CREATE VIEW v_patients AS
SELECT p.id AS patient_id, p.name AS patient_name, p.gender, p.age, p.city, p.region,
       p.insurance, p.signup_date,
       COUNT(DISTINCT v.id) AS visit_count,
       COUNT(DISTINCT CASE WHEN v.status='completed' THEN v.id END) AS completed_visit_count,
       ROUND(COALESCE(SUM(CASE WHEN v.status='completed' THEN rx.quantity*rx.unit_price END),0),2) AS completed_amount
FROM patients p
LEFT JOIN visits v ON v.patient_id=p.id
LEFT JOIN prescriptions rx ON rx.visit_id=v.id
GROUP BY p.id;

-- 药品销售汇总: 一行 = 一个药品, 药品排行用它
DROP VIEW IF EXISTS v_drugs;
CREATE VIEW v_drugs AS
SELECT rx.drug_name, rx.drug_category,
       ROUND(MIN(rx.unit_price),2) AS min_unit_price,
       ROUND(MAX(rx.unit_price),2) AS max_unit_price,
       COALESCE(SUM(rx.quantity),0) AS qty,
       COUNT(rx.id) AS line_count,
       COUNT(DISTINCT rx.visit_id) AS visit_count,
       ROUND(COALESCE(SUM(rx.quantity*rx.unit_price),0),2) AS amount
FROM prescriptions rx
GROUP BY rx.drug_name, rx.drug_category;
"""

if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    conn.executescript(VIEWS)
    counts = {}
    for v in ("v_rx", "v_visits", "v_patients", "v_drugs"):
        counts[v] = conn.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
    conn.close()
    print("views:", counts)
