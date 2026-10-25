# -*- coding: utf-8 -*-
"""评测runner: 按版本跑150用例, 输出能力梯度。
用法: python eval/runner.py --agent v0_bare --suite all --limit 5 --workers 4
"""
import os
import sys
import json
import time
import argparse
import importlib
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "agent"))
sys.path.insert(0, os.path.join(BASE, "eval"))

from checker import score_case  # noqa


def load_agent(name):
    mod = importlib.import_module(name)
    return mod.AgentV0 if name == "v0_bare" else getattr(mod, f"Agent{name[0].upper()}{name[1]}".replace("v_", "V"))


def agent_class(name):
    mod = importlib.import_module(name)
    cands = [getattr(mod, a) for a in dir(mod)
             if a.startswith("Agent") and a != "BaseAgent"
             and getattr(mod, a).__module__ == mod.__name__]
    if len(cands) != 1:
        raise ImportError(f"module {name} defines {len(cands)} agent classes: {[c.__name__ for c in cands]}")
    return cands[0]


def run_case(cls, case):
    import time as _t
    started = _t.time()
    ag = cls()
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
        answers.append(f"(agent异常: {e})")
    finally:
        try:
            ag.save_trace(case["id"])
        except Exception:
            pass
        ag.cleanup()
    return {"case": case["id"], "answers": answers,
            "n_tool_calls": n_calls, "exec_errors": exec_errors,
            "started": started}


def run_case_subprocess(agent_name, case, timeout=None):
    """单题子进程隔离: 子进程硬崩溃不影响父进程(不稳定后端专用)"""
    import subprocess as sp
    if timeout is None:
        timeout = int(os.environ.get("CASE_TIMEOUT", "900"))
    cdir = os.path.join(BASE, "eval", "_tmp_cases")
    os.makedirs(cdir, exist_ok=True)
    cpath = os.path.join(cdir, f"{case['id']}.in.json")
    opath = os.path.join(cdir, f"{case['id']}.out.json")
    if os.path.exists(opath):
        os.remove(opath)
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False)
    logp = os.path.join(cdir, f"{case['id']}.err.log")
    try:
        with open(logp, "ab") as errf:
            sp.run([sys.executable, "-u", "-X", "utf8", os.path.join(BASE, "eval", "case_worker.py"),
                    cpath, agent_name, opath], timeout=timeout, cwd=BASE,
                   stdout=sp.DEVNULL, stderr=errf)
    except Exception:
        pass
    if os.path.exists(opath):
        try:
            with open(opath, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"case": case["id"], "answers": ["(worker崩溃)"], "n_tool_calls": 0,
            "exec_errors": 1, "started": time.time()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--suite", default="all", choices=["all", "sql", "pandas", "tool"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="逗号分隔case id")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--subprocess", action="store_true",
                    help="每题独立子进程(崩溃隔离), 不稳定后端使用")
    args = ap.parse_args()

    with open(os.path.join(BASE, "eval", "cases.json"), encoding="utf-8") as f:
        CASES = json.load(f)
    todo = []
    for suite, lst in CASES.items():
        if args.suite != "all" and suite != args.suite:
            continue
        todo.extend(lst)
    if args.only:
        ids = set(args.only.split(","))
        todo = [c for c in todo if c["id"] in ids]
    if args.limit:
        todo = todo[:args.limit]

    cls = agent_class(args.agent)
    out = os.path.join(BASE, "eval", "results", f"{args.agent}_{args.suite}.json")
    # 断点续跑: 已有结果且答案非"(agent异常"的用例跳过
    done_map = {}
    if os.path.exists(out) and not args.only:
        try:
            with open(out, encoding="utf-8") as f:
                for d in json.load(f):
                    if d.get("answers") and "(agent异常" not in d["answers"][0] and "(runner异常" not in d["answers"][0]:
                        done_map[d["case"]] = d
        except Exception:
            done_map = {}
    todo_run = [c for c in todo if c["id"] not in done_map]
    print(f"[{args.agent}] total={len(todo)} resumed={len(done_map)} to_run={len(todo_run)} workers={args.workers}", flush=True)
    details = list(done_map.values())
    if todo_run:
        def target(c):
            if args.subprocess:
                return run_case_subprocess(args.agent, c)
            return run_case(cls, c)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(target, c): c for c in todo_run}
            done = 0
            for fut in as_completed(futs):
                c = futs[fut]
                try:
                    res = fut.result()
                except Exception:
                    res = {"case": c["id"], "answers": ["(runner异常)"], "n_tool_calls": 0, "exec_errors": 1}
                    traceback.print_exc()
                m = score_case(c, res, args.agent, res.get("started"))
                m["answers"] = res["answers"]
                details.append(m)
                done += 1
                if done % 10 == 0 or done == len(todo_run):
                    print(f"  {done}/{len(todo_run)}", flush=True)
        # 每次都全量重写, 保持顺序稳定
        order = {c["id"]: i for i, c in enumerate(todo)}
        details.sort(key=lambda d: order.get(d["case"], 9999))
        with open(out, "w", encoding="utf-8") as f:
            json.dump(details, f, ensure_ascii=False, indent=1)
        # 归档: 每次运行按 模型+时间戳 留存逐题结果(供跨模型/跨版本重叠分析)
        import shutil
        from common import MODEL_ID
        arch_dir = os.path.join(BASE, "eval", "results", "archive")
        os.makedirs(arch_dir, exist_ok=True)
        arch = os.path.join(arch_dir, f"{MODEL_ID.replace('/', '_').replace(':', '_')}_{args.agent}_{args.suite}_{time.strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copyfile(out, arch)
        print("archived ->", arch)

    # 汇总
    def pct(x, n):
        return f"{100.0 * x / n:.1f}%" if n else "-"

    print(f"\n==== {args.agent} 结果 ====")
    print(f"{'套件':8}{'N':>4}{'工具OK':>9}{'执行OK':>9}{'最终答对':>9}{'全程答对':>9}")
    for suite in ("sql", "pandas", "tool"):
        ds = [d for d in details if d["suite"] == suite]
        if not ds:
            continue
        n = len(ds)
        print(f"{suite:8}{n:>4}"
              f"{pct(sum(d['tool_ok'] for d in ds), n):>9}"
              f"{pct(sum(d['exec_ok'] for d in ds), n):>9}"
              f"{pct(sum(d['answer_ok'] for d in ds), n):>9}"
              f"{pct(sum(d['all_turns_ok'] for d in ds), n):>9}")
    n = len(details)
    print(f"{'合计':8}{n:>4}"
          f"{pct(sum(d['tool_ok'] for d in details), n):>9}"
          f"{pct(sum(d['exec_ok'] for d in details), n):>9}"
          f"{pct(sum(d['answer_ok'] for d in details), n):>9}"
          f"{pct(sum(d['all_turns_ok'] for d in details), n):>9}")
    print("saved ->", out)


if __name__ == "__main__":
    main()
