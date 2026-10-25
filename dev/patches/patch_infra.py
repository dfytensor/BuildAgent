# -*- coding: utf-8 -*-
"""基础设施加固(问题无关):
1. chat() 最终失败时把LLM错误归类写日志(免费日配额/上游拥塞/其他)
2. runner 子进程 stderr 落盘(不再盲盒)
"""
import pathlib

LOG_SNIPPET = '''        except Exception as e:
            if attempt == 5:
                try:
                    _d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "_tmp_cases")
                    os.makedirs(_d, exist_ok=True)
                    with open(os.path.join(_d, "llm_errs.log"), "a", encoding="utf-8") as _f:
                        _f.write(f"{time.strftime('%m-%d %H:%M:%S')} {type(e).__name__}: {str(e)[:220]}\\n")
                except Exception:
                    pass
                raise'''

p = pathlib.Path(r"agent\common.py")
t = p.read_text(encoding="utf-8")
old = '''        except Exception as e:
            if attempt == 5:
                raise'''
assert old in t, "chat except block not found"
t = t.replace(old, LOG_SNIPPET, 1)

r = pathlib.Path(r"eval\runner.py")
t2 = r.read_text(encoding="utf-8")
old2 = '''    try:
        sp.run([sys.executable, "-u", "-X", "utf8", os.path.join(BASE, "eval", "case_worker.py"),
                cpath, agent_name, opath], timeout=timeout, cwd=BASE,
               stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    except Exception:
        pass'''
new2 = '''    logp = os.path.join(cdir, f"{case['id']}.err.log")
    try:
        with open(logp, "ab") as errf:
            sp.run([sys.executable, "-u", "-X", "utf8", os.path.join(BASE, "eval", "case_worker.py"),
                    cpath, agent_name, opath], timeout=timeout, cwd=BASE,
                   stdout=sp.DEVNULL, stderr=errf)
    except Exception:
        pass'''
assert old2 in t2, "run_case_subprocess block not found"
t2 = t2.replace(old2, new2, 1)

p.write_text(t, encoding="utf-8")
r.write_text(t2, encoding="utf-8")
print("patched: chat err log + runner stderr capture")
