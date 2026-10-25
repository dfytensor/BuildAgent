# -*- coding: utf-8 -*-
"""沙盒子进程: 执行 pandas/matplotlib 代码, stdout 输出 JSON 结果。
可选命名空间持久化(_ns_file): 同一会话多步分析时变量保留, 避免重复读库。
"""
import sys
import json
import os
import io
import contextlib
import pickle
import traceback


def main():
    task_path = sys.argv[1]
    with open(task_path, encoding="utf-8") as f:
        task = json.load(f)
    code, db, out_dir = task["code"], task["db"], task["out_dir"]
    ns_file = task.get("_ns_file")

    import pandas as pd
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False

    ns = {"pd": pd, "np": np, "plt": plt, "out_dir": out_dir}
    if ns_file and os.path.exists(ns_file) and task.get("keep_ns"):
        try:
            with open(ns_file, "rb") as f:
                ns.update(pickle.load(f))
        except Exception:
            pass
    if "conn" not in ns or ns.get("conn") is None:
        import sqlite3
        ns["conn"] = sqlite3.connect(db)

    buf = io.StringIO()
    ok, err = True, None
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, ns)  # 演示级沙盒: 已在上游做静态黑名单
    except Exception:
        ok = False
        err = traceback.format_exc(limit=3)[-900:]

    # 命名空间持久化(仅保留轻量对象)
    if ns_file and task.get("keep_ns"):
        keep = {}
        for k, v in ns.items():
            if k.startswith("__") or k in ("pd", "np", "plt", "conn"):
                continue
            try:
                pickle.dumps(v)
                keep[k] = v
            except Exception:
                pass
        try:
            with open(ns_file, "wb") as f:
                pickle.dump(keep, f)
        except Exception:
            pass

    stdout = buf.getvalue()
    print(json.dumps({"ok": ok, "error": err, "stdout": stdout[-1800:]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
