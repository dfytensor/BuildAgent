# -*- coding: utf-8 -*-
"""医院门诊领域配置(第二领域验证): schema / 口径 / 提示词 / 工具集
用法: hospital 系列代理在 import 时把 v4_sandbox 的 PLANNER_SYS/TOOLS_SPEC 替换为本配置。
对应方法论 §2.5.10 的"域配置层"——换领域=换一个配置文件, 不改脚手架代码。
"""

# ---------- schema + 业务口径 ----------
import os
import sqlite3

HOSP_SCHEMA = """库:SQLite hospital.db(医院门诊)
patients(患者): id, name姓名, gender性别[男/女], age年龄, city城市, region区域[华东/华北/华南/西南/东北], insurance医保类型[城镇职工/城乡居民/自费], signup_date建档日期
departments(科室): id, name科室名[内科/外科/儿科/骨科/妇产科/眼科/皮肤科/耳鼻喉科], floor楼层
doctors(医生): id, name姓名, department_id→departments.id, title职称[主任医师/副主任医师/主治医师/住院医师], fee挂号费
visits(就诊): id, patient_id→patients.id, doctor_id→doctors.id, visit_date就诊时间, status状态[已完成/已取消/待诊], vtype类型[门诊/急诊/复诊]
prescriptions(处方明细): id, visit_id→visits.id, drug_name药品名, drug_category药品类目[抗生素/中成药/解热镇痛/维生素/慢性病用药/消化用药], quantity数量, unit_price单价
口径: 处方金额=SUM(quantity*unit_price); 只统计已完成就诊须加 visits.status='completed'
"""

# ---------- 基线提示词(v9h): schema + 方言 + 口径 + 任务, 无数据源地图/无指标工具 ----------
HOSP_PLANNER_BASE = """你是医院门诊数据分析规划器, 已连接本医院数据库(工具可直接查询全部业务数据)。
业务规则:
- 处方金额 = SUM(quantity*unit_price); 只统计已完成就诊须加 visits.status='completed'
- status枚举: completed已完成/cancelled已取消/pending待诊; vtype类型: 门诊/急诊/复诊
- insurance医保类型: 城镇职工/城乡居民/自费; 科室: 内科/外科/儿科/骨科/妇产科/眼科/皮肤科/耳鼻喉科
- 表结构已在工具描述中给出, 禁止查询sqlite_master/PRAGMA
SQL方言(SQLite, 必须遵守):
- 没有YEAR()/MONTH()函数; 时间用 substr(visit_date,1,4)='2024' 等字符串比较
- 别名用 AS, 字符串用单引号, 不要用反引号
任务: 需要查数据/计算/画图时, 调用工具(一次一步); 闲聊或无需数据时直接文字回答。
计算规则: 对已查到的数值做乘/除/加减/百分比运算时, 必须调用 calculator 工具, expression 用上下文中的具体数值组装, 禁止心算。
注意: 你有数据库查询能力, 禁止回答"无法访问数据/无法获取实时数据"之类拒绝话术。
语义约定: "前N个/最早N个" = 按主键id升序的前N个; 多表关联时注意去重(一位患者/一次就诊可能对应多行明细)。
"""

# ---------- 治理版提示词(v12h): 基线 + 数据源地图 + 指标工具 ----------
HOSP_PLANNER_V12 = HOSP_PLANNER_BASE + """数据源地图(按问题粒度选表, 避免重复行, 不需要JOIN):
- patients: 患者档案(性别/年龄/城市/区域/医保类型/建档日期), 一行=一位患者
- doctors: 医生(科室/职称/挂号费), 一行=一位医生
- visits: 就诊头(状态/类型/患者id/医生id/时间), 一行=一次就诊
- prescriptions: 处方明细(药品名/类目/数量/单价), 一行=一个明细
- v_rx: 处方明细宽表(一行=一个处方明细, 含患者/医生/科室/时间), 适合按维度汇总金额/数量; 直接列就诊会重复
- v_visits: 就诊宽表(一行=一次就诊, 含患者/医生/科室/rx_lines/qty/amount), 用于"前N次就诊/就诊总数/每次金额"
- v_patients: 患者宽表(一行=一位患者, 含visit_count/completed_visit_count/completed_amount), 用于患者级统计
- v_drugs: 药品汇总(一行=一个药品, 含qty/line_count/amount), 用于药品排行
选表规则: 就诊级问题用 v_visits; 药品排行用 v_drugs; 患者统计用 v_patients; 明细/维度汇总用 v_rx; 患者属性用 patients。
指标工具: hosp_metric 支持 visit_count/completed_visit_count/rx_amount/rx_lines/patient_count/doctor_count/drug_kinds/avg_cost_per_visit, 口径自动保证, 优先使用, 不要再用自写SQL覆盖它。
"""

# ---------- 工具集 ----------
def _sq_desc():
    return ("执行只读SQL查询。按粒度选表: patients(患者档案)、doctors(医生)、departments(科室)、"
            "visits(就诊头)、prescriptions(处方明细)、v_rx(处方明细宽表,一行=一个处方明细,按维度汇总用)、"
            "v_visits(就诊宽表,一行=一次就诊,就诊级问题用)、v_patients(患者宽表)、v_drugs(药品汇总)。"
            "除v_rx外单表即可,无需JOIN。")

def _load_df_desc():
    return ("把一条简单SELECT的结果加载为沙盒里的 DataFrame(df_1,df_2...), "
            "供 run_python 做 JOIN/聚合/排序/多步计算。只写简单SELECT(选列+基本WHERE/LIMIT), "
            "不要多表JOIN/子查询。")

def _calc_desc():
    return ("数值计算器(推荐)。对上下文中已查到的数值做乘/除/加减/百分比运算时必须用本工具, 不要心算。"
            "expression用具体数值组装。")


def _hosp_metric_desc():
    return ("医院业务指标查询(推荐, 口径自动保证, 优先于手写SQL)。"
            "metric: visit_count=就诊人次(默认全部状态)/completed_visit_count=已完成就诊人次/"
            "rx_amount=处方金额(默认只算已完成)/rx_lines=处方明细行数/patient_count=患者人数/"
            "doctor_count=医生人数/drug_kinds=药品种数(按药品名去重)/avg_cost_per_visit=已完成就诊的次均处方金额; "
            "需要全状态(含已取消)时传 status='all'。"
            "dim分组: month/year/department/vtype/status/insurance/region或none。"
            "year仅填问题中出现的年份如\"2024\"。")


def _sql_tool():
    return {"type": "function", "function": {
        "name": "sqlite_query",
        "description": _sq_desc(),
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "SQLite SELECT语句"}}, "required": ["sql"]}}}


def _load_df_tool():
    return {"type": "function", "function": {
        "name": "load_df",
        "description": _load_df_desc(),
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "简单SELECT语句"}}, "required": ["sql"]}}}


def _run_python_tool():
    return {"type": "function", "function": {
        "name": "run_python",
        "description": "执行pandas/matplotlib代码。已预置pd,np,plt,conn(医院库连接),out_dir; "
                       "严禁import和connect; 8行内; 最后print结果。",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string"}}, "required": ["code"]}}}


def _calc_tool():
    return {"type": "function", "function": {
        "name": "calculator",
        "description": _calc_desc(),
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string"}}, "required": ["expression"]}}}


def _hosp_metric_tool():
    return {"type": "function", "function": {
        "name": "hosp_metric",
        "description": _hosp_metric_desc(),
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string"}, "dim": {"type": "string"},
            "year": {"type": "string"}, "status": {"type": "string"}}}}}


HOSP_TOOLS_BASE = [_sql_tool(), _run_python_tool(), _calc_tool()]
HOSP_TOOLS_V12 = HOSP_TOOLS_BASE + [_load_df_tool(), _hosp_metric_tool()]


# ---------- 指标注册表工具(口径沉入代码) ----------
def hosp_metric(args, state=None):
    metric = str(args.get("metric", "")).strip()
    dim = str(args.get("dim") or "none").lower()
    year = args.get("year")
    status = args.get("status")
    dims = {"month": "month", "year": "year", "department": "department",
            "vtype": "vtype", "status": "status", "insurance": "insurance",
            "region": "region"}
    if dim != "none" and dim not in dims:
        return {"ok": False, "error": f"dim须为{sorted(dims)}"}
    if status == "all":
        eff = None
    elif status not in (None, ""):
        eff = status
    else:
        eff = "completed" if metric in ("rx_amount", "completed_visit_count", "avg_cost_per_visit") else None
    where, params = [], []
    if eff:
        where.append("status = ?")
        params.append(eff)
    if year not in (None, ""):
        where.append("year = ?")
        params.append(str(year))
    simple = {"visit_count": "COUNT(*)",
              "completed_visit_count": "SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END)",
              "rx_amount": "ROUND(SUM(CASE WHEN status='completed' THEN amount ELSE 0 END),2)",
              "rx_lines": "SUM(rx_lines)",
              "avg_cost_per_visit":
              "ROUND(SUM(CASE WHEN status='completed' THEN amount ELSE 0 END)"
              "*1.0/NULLIF(SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),0),2)"}
    if metric == "patient_count":
        sql = "SELECT COUNT(*) FROM patients"
    elif metric == "doctor_count":
        sql = "SELECT COUNT(*) FROM doctors"
    elif metric == "drug_kinds":
        sql = "SELECT COUNT(DISTINCT drug_name) FROM prescriptions"
    elif metric in simple:
        sql = f"SELECT {simple[metric]} FROM v_visits"
    else:
        return {"ok": False, "error": f"metric须为 visit_count/completed_visit_count/rx_amount/"
                                      f"rx_lines/avg_cost_per_visit/patient_count/doctor_count/drug_kinds, 得到 {metric}"}
    colname = dims.get(dim, dim)
    if metric in simple and dim != 'none':
        sql = f'SELECT {colname} AS label, {simple[metric]} AS value FROM v_visits'
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    if metric in simple and dim != 'none':
        sql += f' GROUP BY {colname} ORDER BY {colname}'
    try:
        rows = [tuple(r) for r in sqlite3.connect(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'hospital.db')).execute(sql, params).fetchall()]
    except Exception as e:
        return {'ok': False, 'error': f'{type(e).__name__}: {e}'}
    vals = [v for r in rows for v in r]
    cols = [colname, 'value'] if (metric in simple and dim != 'none') else ['value']
    return {'ok': True, 'metric': metric, 'columns': cols, 'rows': rows, 'values': vals,
            'note': '口径: 见工具描述' + (f', status={eff}' if eff else '')}


from common import register_tool as _register
_register("hosp_metric", hosp_metric)
