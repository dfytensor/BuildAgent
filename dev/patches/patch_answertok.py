# -*- coding: utf-8 -*-
"""答案器预算可配置: ANSWER_TOK 环境变量(默认3000); DeepSeek思考型需更大"""
import os
import pathlib

p = pathlib.Path(r"agent\v4_sandbox.py")
t = p.read_text(encoding="utf-8")

if "\nimport os\n" not in t:
    t = t.replace("import re\nimport json", "import os\nimport re\nimport json", 1)

old = "ans = chat(self._answer_msgs(user_text, observations), temperature=0.0, max_tokens=3000)"
new = ('ans = chat(self._answer_msgs(user_text, observations), temperature=0.0, '
       'max_tokens=int(os.environ.get("ANSWER_TOK", "3000")))')
assert old in t, "answerer line not found"
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("ANSWER_TOK applied")