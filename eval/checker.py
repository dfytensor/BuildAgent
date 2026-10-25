# -*- coding: utf-8 -*-
"""自动判分: 数值容差匹配 + 文本包含匹配 + 图表文件校验"""
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS = os.path.join(BASE, "artifacts")

NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def extract_numbers(text):
    out = []
    for m in NUM_RE.finditer(text or ""):
        s = m.group(0).replace(",", "")
        try:
            v = float(s)
        except ValueError:
            continue
        # 处理中文单位
        tail = (text[m.end():m.end() + 2]).lstrip()
        if tail.startswith("万"):
            v *= 10000
        elif tail.startswith("亿"):
            v *= 100000000
        out.append(v)
    return out


def num_eq(a, b):
    if a == b:
        return True
    tol = max(0.011, abs(b) * 0.005)
    if abs(a - b) <= tol:
        return True
    # 单位等价: 百分数 vs 小数 (100.0% == 1.0)
    if b != 0 and abs(a * 100 - b) <= max(0.011, abs(b) * 0.005):
        return True
    if a != 0 and abs(a - b * 100) <= max(0.011, abs(a) * 0.005):
        return True
    return False


def _flatten_gold(vals):
    out = []
    for v in vals:
        if isinstance(v, (list, tuple)):
            out.extend(_flatten_gold(list(v)))
        else:
            out.append(v)
    return out


def match_values(gold_values, text):
    gold_values = _flatten_gold(gold_values)
    """gold 中每个标量都要在答案文本中出现(数值容差/字符串包含)"""
    missing = []
    nums = extract_numbers(text)
    low = (text or "").lower()
    for v in gold_values:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if not any(num_eq(n, float(v)) for n in nums):
                missing.append(v)
        else:
            if str(v).lower() not in low:
                missing.append(v)
    return (len(missing) == 0), missing


def chart_file_ok(question, case_start=None):
    """图必须存在 且 (给了case_start时)是本轮新生成的, 防跨轮残留文件假阳性"""
    m = re.search(r"(chart_\w+\.png)", question or "")
    if not m:
        return True
    p = os.path.join(ARTIFACTS, m.group(1))
    if not (os.path.exists(p) and os.path.getsize(p) > 5000):
        return False
    if case_start is not None:
        return os.path.getmtime(p) >= case_start - 2
    return True


def score_turn(gold, answer):
    if gold is None:
        return True, []
    if gold.get("kind") == "chart":
        return True, []
    ok, missing = match_values(gold.get("values", []), answer)
    return ok, missing


def score_case(case, result, agent_name, case_start=None):
    """result: {"answers": [每轮答案], "n_tool_calls": int, "exec_errors": int}"""
    m = {"case": case["id"], "suite": None, "level": case["level"],
         "answer_ok": False, "all_turns_ok": False, "tool_ok": False,
         "exec_ok": False, "chart_ok": True}
    suite = case["id"].split("-")[0]
    m["suite"] = {"SQL": "sql", "PY": "pandas", "TOOL": "tool"}.get(suite, suite)

    answers = result["answers"]
    if case.get("turns"):
        golds = [t["gold"] for t in case["turns"]["turns"]]
        finals = []
        ok_all = True
        for i, g in enumerate(golds):
            if g is None or not g.get("values"):
                continue
            ans = answers[i] if i < len(answers) else ""
            ok, missing = score_turn(g, ans)
            if not ok:
                ok_all = False
        m["all_turns_ok"] = ok_all
        m["answer_ok"] = score_turn(golds[-1], answers[-1] if answers else "")[0]
    else:
        ok, _ = score_turn(case["gold"], answers[0] if answers else "")
        m["answer_ok"] = ok
        m["all_turns_ok"] = ok

    # 图表类
    if case["gold"] and case["gold"].get("kind") == "chart":
        m["chart_ok"] = chart_file_ok(case["q"], case_start)
        m["answer_ok"] = m["answer_ok"] and m["chart_ok"]

    m["tool_ok"] = result["n_tool_calls"] >= case.get("min_calls", 1)
    m["exec_ok"] = result["n_tool_calls"] >= case.get("min_calls", 1) and result["exec_errors"] == 0
    return m
