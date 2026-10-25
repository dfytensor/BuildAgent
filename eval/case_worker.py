# -*- coding: utf-8 -*-
"""单题子进程worker: 崩溃隔离(spark/OpenRouter等不稳定后端可能硬崩溃父进程)
argv: case_json_path agent_name out_json_path
"""
import sys
import json
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "agent"))
sys.path.insert(0, BASE)


def main():
    case_path, agent_name, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    case = json.load(open(case_path, encoding="utf-8"))

    import importlib
    mod = importlib.import_module(agent_name)
    cls = None
    for attr in dir(mod):
        o = getattr(mod, attr)
        if attr.startswith("Agent") and attr != "BaseAgent" and getattr(o, "__module__", "") == mod.__name__:
            cls = o
    if cls is None:
        json.dump({"error": "agent class not found"}, open(out_path, "w", encoding="utf-8"))
        return

    from checker import score_case
    ag = cls()
    started = time.time()
    answers, n_calls, exec_errors = [], 0, 0
    try:
        turns = case["turns"]["turns"] if case.get("turns") else [{"q": case["q"]}]
        for t in turns:
            ans = ag.ask(t["q"])
            answers.append(ans)
            for st in ag.trace[-1]["steps"]:
                n_calls += 1
                if not st["result"].get("ok", False):
                    exec_errors += 1
    except Exception as e:
        answers.append(f"(agent异常: {type(e).__name__}: {e})")
    finally:
        try:
            ag.save_trace(case["id"])
        except Exception:
            pass
        ag.cleanup()

    res = {"case": case["id"], "answers": answers,
           "n_tool_calls": n_calls, "exec_errors": exec_errors, "started": started}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    print(f"WORKER_DONE {case['id']}")


if __name__ == "__main__":
    main()
