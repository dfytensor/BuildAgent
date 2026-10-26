# -*- coding: utf-8 -*-
"""补 dev/ 目录: 探针/诊断/补丁脚本 + 密钥清洗 + 路径可移植化"""
import os
import re
import shutil

SRC = r"F:\智能数据分析agent\eval"
DST = r"C:\Users\Administrator\AppData\Local\Temp\opencode\BuildAgent-check\dev"

GROUPS = {
    "probes": [
        "t_or_probe.py", "t_probe2.py", "t_cands.py", "t_xingchen.py", "t_xing_patience.py",
        "t_8080.py", "t_8080_b.py", "t_8080_fix.py", "t_spark_modes.py", "t_stable.py",
        "t_ds_models.py", "t_ds_probe.py", "t_damage.py", "t_firsttoken.py",
    ],
    "diagnostics": [
        "t_ds_fail_audit.py", "t_gold_check.py", "t_improve_scan.py", "t_qm_usage.py",
        "t_repro1.py", "t_repro2.py", "t_ds_l901.py", "t_ds_l901b.py",
        "t_rep18_compare.py", "t_spark_v11d_report.py", "t_tax.py",
        "t_v11d_check.py", "t_v11_1_values.py", "t_check2.py",
    ],
    "patches": [
        "patch_v11b.py", "patch_v11c.py", "patch_v11_1.py", "patch_budget.py",
        "patch_answertok.py", "patch_thinkoff.py", "patch_emptyretry.py", "patch_infra.py",
    ],
}

KEY_RE = re.compile(r"sk-or-v1-[A-Za-z0-9]{10,}|sk-[0-9a-fA-F]{24,}")
AUTH_RE = re.compile(r'C:\\\\Users\\\\Administrator\\\\\.local\\\\share\\\\opencode\\\\auth\.json|'
                    r'C:\\Users\\Administrator\\.local\\share\\opencode\\auth\.json')

n_total = 0
for group, files in GROUPS.items():
    outdir = os.path.join(DST, group)
    os.makedirs(outdir, exist_ok=True)
    for f in files:
        src = os.path.join(SRC, f)
        if not os.path.exists(src):
            print("MISSING", f)
            continue
        t = open(src, encoding="utf-8").read()
        # 密钥占位
        t = KEY_RE.sub('os.environ.get("OPENROUTER_API_KEY", "")', t)
        # auth.json 路径可移植化
        t = t.replace(r"C:\Users\Administrator\.local\share\opencode\auth.json",
                      os.path.expanduser("~/.local/share/opencode/auth.json"))
        # 确保 import os
        if "import os" not in t.split("\n\n")[0] and "os.environ" in t:
            lines = t.splitlines()
            # 在第一个 import 前插入
            for i, ln in enumerate(lines):
                if ln.startswith("import ") or ln.startswith("from "):
                    lines.insert(i, "import os")
                    break
            else:
                lines.insert(0, "import os")
            t = "\n".join(lines)
        open(os.path.join(outdir, f), "w", encoding="utf-8").write(t)
        n_total += 1

print("dev files:", n_total)
