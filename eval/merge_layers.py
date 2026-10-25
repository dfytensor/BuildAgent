# -*- coding: utf-8 -*-
"""通用层叠合并: 基础归档 + 当前指针(重跑子集) -> 合并文件"""
import json
import sys
import collections

base_p = sys.argv[1]
overlay_p = sys.argv[2]
out_p = sys.argv[3]

base = json.load(open(base_p, encoding="utf-8"))
overlay = {c["case"]: c for c in json.load(open(overlay_p, encoding="utf-8"))}
merged = [overlay.get(c["case"], c) for c in base]
json.dump(merged, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

ok = sum(1 for c in merged if c.get("answer_ok"))
by = collections.defaultdict(lambda: [0, 0])
for c in merged:
    by[c["suite"]][1] += 1
    by[c["suite"]][0] += 1 if c.get("answer_ok") else 0
print(f"merged -> {out_p}")
print(f"total {ok}/{len(merged)} = {ok/len(merged)*100:.1f}%")
for s in ("sql", "pandas", "tool"):
    o, n = by[s]
    print(f"  {s}: {o}/{n} = {o/n*100:.0f}%")
infra = [c["case"] for c in merged if any(m in json.dumps(c.get("answers", []), ensure_ascii=False)
                                          for m in ("回答失败", "worker崩溃", "agent异常"))]
print("基建标记:", infra or "无")
