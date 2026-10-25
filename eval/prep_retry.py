# -*- coding: utf-8 -*-
"""剔除调用失败的minimax用例 → 待重跑; 删除其trace"""
import json
import os
import glob

BAD = ("回答失败", "LLM调用失败", "ConnectionError", "APIConnectionError", "worker崩溃")
fp = r"eval\results\v9_scaffold_all.json"
d = json.load(open(fp, encoding="utf-8"))
retry, keep = [], []
for x in d:
    a = " ".join(x.get("answers", []))
    if any(b in a for b in BAD):
        retry.append(x["case"])
    else:
        keep.append(x)
json.dump(keep, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"保留 {len(keep)}, 待重跑 {len(retry)}: {retry}")
for cid in retry:
    for f in glob.glob(rf"artifacts\trace\v9_scaffold_{cid}.json"):
        os.remove(f)
print("traces cleaned")
