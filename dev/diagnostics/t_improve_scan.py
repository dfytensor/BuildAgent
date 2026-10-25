# -*- coding: utf-8 -*-
"""失败可干预性分类: 空结果类 / 信息缺失类 / 无工具类 / 其它(纯语义)"""
import json
import collections

cases = json.load(open(r"eval\results\spark_v9_off_full.json", encoding="utf-8"))
cats = collections.Counter()
lists = collections.defaultdict(list)
for c in cases:
    if c.get("answer_ok"):
        continue
    a = json.dumps(c.get("answers", []), ensure_ascii=False)
    cid = c["case"]
    if not c.get("tool_ok"):
        cats["无工具/规划失败"] += 1
        lists["无工具/规划失败"].append(cid)
    elif any(k in a for k in ("0行", "为空", "无数据", "未查询到", "查询结果为空")):
        cats["空结果类"] += 1
        lists["空结果类"].append(cid)
    elif any(k in a for k in ("未提供", "不完整", "缺失", "无法列出")):
        cats["信息缺失类(结果呈现)"] += 1
        lists["信息缺失类(结果呈现)"].append(cid)
    elif any(k in a for k in ("查询失败", "无法", "失败")):
        cats["诚实失败类"] += 1
        lists["诚实失败类"].append(cid)
    else:
        cats["纯语义错(答了但错)"] += 1
        lists["纯语义错(答了但错)"].append(cid)

print("失败总数:", sum(cats.values()))
for k, v in cats.most_common():
    print(f"  {k}: {v}")
    print(f"    {lists[k][:12]}")
