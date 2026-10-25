# -*- coding: utf-8 -*-
"""回答器预算加宽(修思考截断): 700->2000, chat兜底 400->1500"""
import pathlib

p = pathlib.Path(r"agent\v4_sandbox.py")
t = p.read_text(encoding="utf-8")

old1 = """                    ans = chat(self._answer_msgs(user_text, observations), temperature=0.0, max_tokens=700)"""
new1 = """                    ans = chat(self._answer_msgs(user_text, observations), temperature=0.0, max_tokens=2000)"""
assert old1 in t
t = t.replace(old1, new1)

old2 = """                    {"role": "user", "content": user_text}]
            try:
                answer = chat(msgs, temperature=0.0, max_tokens=400)"""
assert old2 in t
t = t.replace(old2, old2.replace("max_tokens=400", "max_tokens=1500"))

p.write_text(t, encoding="utf-8")

# v5_memory._answer_msgs 的长度限制会截工具结果, 不动; 但 answer 调用继承 v4 的 max_tokens
print("patched: answerer 2000 tok, chat fallback 1500")
