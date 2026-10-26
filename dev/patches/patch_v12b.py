# -*- coding: utf-8 -*-
"""v12b: 多观测选择
1) 回答器可见每次工具调用的参数(SQL/表达式) + 结果, 便于识别探查性查询
2) ANSWER_SYS 给出明确的选结果优先级(修订优先/列表最全/忽略探查/空错回退)
"""
import pathlib

# ---- 1) v5_memory: 回答器消息带上调用参数 ----
p = pathlib.Path(r"agent\v5_memory.py")
t = p.read_text(encoding="utf-8")
old = """        for i, (call, res) in enumerate(observations):
            content += f"\\n[工具{i+1}结果] {summarize_result(res)}\""""
new = """        for i, (call, res) in enumerate(observations):
            args = (call or {}).get("args", {}) if isinstance(call, dict) else {}
            brief = args.get("sql") or args.get("expression") or args.get("metric") or ""
            if brief:
                content += f"\\n[工具{i+1}调用] {str(brief)[:200]}"
            content += f"\\n[工具{i+1}结果] {summarize_result(res)}\""""
assert old in t, "v5 answer loop not found"
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")

# ---- 2) ANSWER_SYS 选结果优先级 ----
v = pathlib.Path(r"agent\v4_sandbox.py")
t2 = v.read_text(encoding="utf-8")
old2 = ("若结果是多行列表, 必须逐行完整列出全部行(不要只列第一行或做摘要)。若多条工具结果内容冲突, "
        "选择能回答问题且最完整的一条(通常行数最多); 不要用中间探查的小结果覆盖完整结果, 若最后一条是空结果/错误则参考前面成功的结果。"
        "若 calculator 已给出计算结果, 直接采用该结果作答, 不要再说无法计算。")
new2 = ("若结果是多行列表, 必须逐行完整列出全部行(不要只列第一行或做摘要)。\\n"
        "选结果优先级: ①同一指标多次查询时, 以最后一次成功的查询为准(修订优先); "
        "②问题要求列表时, 选行数最多且字段匹配的成功结果; "
        "③忽略 SELECT * ... LIMIT 小数字 这类探查性结果, 不要用它回答; "
        "④若最后一条是0行/错误, 用前一条成功结果。"
        "若 calculator 已给出计算结果, 直接采用该结果作答, 不要再说无法计算。")
assert old2 in t2, "ANSWER_SYS rule not found"
t2 = t2.replace(old2, new2, 1)
v.write_text(t2, encoding="utf-8")
print("v12b patched: observation context + selection priority")
