# -*- coding: utf-8 -*-
"""EXTRA_BODY 默认加 chat_template_kwargs.enable_thinking=false (仅作用于chat()答案格式化路径)"""
import os
import pathlib

p = pathlib.Path(r"agent\common.py")
t = p.read_text(encoding="utf-8")
old = 'EXTRA_BODY = json.loads(os.environ.get("LLM_EXTRA_BODY", "{}"))'
new = ('EXTRA_BODY = json.loads(os.environ.get("LLM_EXTRA_BODY", '
       '\'{"chat_template_kwargs": {"enable_thinking": false}}\'))')
assert old in t
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("EXTRA_BODY defaulted: answerer thinking OFF (planner native path unchanged)")