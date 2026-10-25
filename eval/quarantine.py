# -*- coding: utf-8 -*-
"""按时间窗隔离: 只保留 修复后+代表集 时段 的有效trace, 其余移入invalid目录"""
import os
import glob
import time
import shutil

TRACE = r"artifacts\trace"
INVALID = r"eval\results\invalid_deploy_8020"
os.makedirs(INVALID, exist_ok=True)

# 有效窗: shop.db修复+服务稳定验证之后 (t_stable 6/6 成功时刻起)
cutoff = time.time() - 3600 * 3.5  # 约3.5小时前 = 修复验证时刻
kept, moved = [], 0
for f in glob.glob(os.path.join(TRACE, "v7_general_*.json")):
    if os.path.getmtime(f) >= cutoff:
        kept.append(os.path.basename(f))
    else:
        shutil.move(f, os.path.join(INVALID, os.path.basename(f)))
        moved += 1
print(f"kept={len(kept)} moved_invalid={moved}")
for k in sorted(kept):
    print("  ", k)
