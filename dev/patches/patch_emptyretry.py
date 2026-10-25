# -*- coding: utf-8 -*-
"""通用空答重试: 回答器返回空content时, 提示直接作答再要一次(跨部署通用)"""
import os
import pathlib

p = pathlib.Path(r"agent\v4_sandbox.py")
t = p.read_text(encoding="utf-8")

old = """            ans = ans or "(回答失败)\""""
assert old in t, "answer fallback line not found"
new = """            if not (ans or "").strip():
                # 空答重试: 部分思考模型会把输出预算烧在思考上, 提示直接作答
                try:
                    msgs2 = self._answer_msgs(user_text, observations)
                    msgs2[-1]["content"] += "\\n[要求] 直接输出FINAL和最终答案, 不要重复分析或计算过程。"
                    ans = chat(msgs2, temperature=0.0,
                               max_tokens=int(os.environ.get("ANSWER_TOK", "3000")))
                except Exception:
                    pass
            ans = ans or "(回答失败)\""""
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("empty-answer retry added")