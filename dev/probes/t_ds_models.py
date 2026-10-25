# -*- coding: utf-8 -*-
"""DeepSeek 官方API探活: /models + 基础QA + 原生tools + 思考字段"""
import json
import os
import time
import requests

AUTH = json.load(open(os.path.expanduser("~/.local/share/opencode/auth.json"), encoding="utf-8"))
KEY = AUTH["deepseek"]["key"]
BASE = "https://api.deepseek.com/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

print("== /models ==")
try:
    r = requests.get(f"{BASE}/models", headers=H, timeout=30)
    print("HTTP", r.status_code)
    data = r.json().get("data", [])
    for m in data:
        print("  ", m.get("id"))
except Exception as e:
    print("FAIL", type(e).__name__, str(e)[:120])
