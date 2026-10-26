# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, "agent")
from v4_sandbox import parse_tool_call

rwkv_out = """<tool_calls>
[
{"name": "run_query", "arguments": {"sql": "SELECT COUNT(*) FROM products"}}
]
</tool_calls>"""
print("rwkv:", parse_tool_call(rwkv_out))
print("legacy:", parse_tool_call('TOOL {"tool":"sqlite_query","args":{"sql":"SELECT 1"}}'))
print("none:", parse_tool_call("你好, 我不知道"))
