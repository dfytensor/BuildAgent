#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""probe — LLM endpoint deployment health check for agent scaffolds.

Runs a 7-step fingerprint against an OpenAI-compatible endpoint and prints
a PASS/WARN/FAIL report plus a recommended scaffold configuration.

Usage:
  python probe/probe.py --base-url http://127.0.0.1:8080/v1
  python probe/probe.py --base-url https://api.deepseek.com/v1 --model deepseek-flash --api-key sk-... --full
"""
import argparse
import concurrent.futures
import json
import os
import sys
import time

import requests

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


class Probe:
    def __init__(self, base_url, model=None, api_key="none", timeout=180):
        self.base = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or "none"
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {"Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"}
        self.report = []
        self.think_extra = None
        self.reco = {"ANSWER_TOK": 3000, "LLM_TOK_CAP": 3000,
                     "LLM_EXTRA_BODY": "{}", "ANSWER_CTX": "0"}

    # ---------- low level ----------
    def chat(self, messages, max_tokens=512, tools=None, extra=None, temperature=0.0):
        body = {"model": self.model, "messages": messages,
                "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            body["tools"] = tools
        if extra:
            body.update(extra)
        t0 = time.time()
        r = self.session.post(f"{self.base}/chat/completions", headers=self.headers,
                              data=json.dumps(body), timeout=self.timeout)
        dt = time.time() - t0
        try:
            data = r.json()
        except Exception:
            data = {}
        return dt, r.status_code, data

    def log(self, step, status, msg):
        self.report.append((step, status, msg))
        print(f"[{status:4s}] {step:24s} {msg}")

    # ---------- steps ----------
    def step_models(self):
        for path in ("/models", "/health"):
            try:
                r = self.session.get(self.base + path, headers=self.headers, timeout=15)
                if r.status_code == 200:
                    self.log("connectivity", PASS, f"{self.base}{path} -> 200")
                    if self.model is None:
                        try:
                            ids = [m.get("id") or m.get("name") for m in r.json().get("data", [])]
                            self.model = ids[0] if ids else self.model
                            self.log("connectivity", PASS, f"auto model = {self.model}")
                        except Exception:
                            pass
                    return True
            except Exception:
                continue
        self.log("connectivity", FAIL, "no /models or /health endpoint reachable")
        return False

    def step_qa(self):
        dt, code, d = self.chat([{"role": "user", "content": "1+1等于几? 只回答数字"}], 100)
        if code != 200:
            self.log("basic-qa", FAIL, f"HTTP {code}: {str(d)[:120]}")
            return
        m = d["choices"][0].get("message", {})
        content = (m.get("content") or "").strip()
        u = d.get("usage", {})
        rt = u.get("completion_tokens_details", {}).get("reasoning_tokens")
        if not content:
            self.log("basic-qa", FAIL, f"empty content ({dt:.1f}s)")
        elif "2" not in content:
            self.log("basic-qa", WARN, f"unexpected answer: {content[:60]}")
        else:
            self.log("basic-qa", PASS, f"'{content[:20]}' ({dt:.1f}s, {u.get('completion_tokens')} tok, reasoning={rt})")
        self._qa_meta = {"reasoning": rt, "latency": dt}

    def step_tools(self):
        tools = [{"type": "function", "function": {
            "name": "run_query",
            "description": "Run a read-only SQL query",
            "parameters": {"type": "object",
                           "properties": {"sql": {"type": "string"}},
                           "required": ["sql"]}}}]
        msgs = [{"role": "system", "content": "You have a run_query tool. Use it when you need data."},
                {"role": "user", "content": "How many products are in the database? Query it."}]
        dt, code, d = self.chat(msgs, 600, tools=tools)
        if code != 200:
            self.log("native-tools", FAIL, f"HTTP {code}")
            return
        ch = d["choices"][0]
        m = ch.get("message", {})
        tcs = m.get("tool_calls")
        if ch.get("finish_reason") == "tool_calls" and tcs:
            fn = tcs[0]["function"]
            self.log("native-tools", PASS, f"tool_calls: {fn['name']}({str(fn.get('arguments'))[:60]})")
        elif tcs:
            self.log("native-tools", WARN, "tool_calls present but finish_reason != tool_calls")
        else:
            self.log("native-tools", FAIL, "no tool_calls returned (text-only fallback needed)")

    def step_reasoning(self):
        msgs = [{"role": "user", "content": "1+1等于几? 只回答数字"}]
        dt, code, d = self.chat(msgs, 200)
        if code != 200:
            self.log("reasoning-posture", FAIL, f"HTTP {code}")
            return
        m = d["choices"][0].get("message", {})
        rc = (m.get("reasoning_content") or "").strip()
        rt = d.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens")
        self.think_extra = None
        if rc or rt:
            self.log("reasoning-posture", WARN,
                     f"reasoning model (reasoning_tokens={rt}). "
                     "Answer path should use budget 6000 and empty-answer retry.")
            self.reco["ANSWER_TOK"] = 6000
            self.reco["LLM_TOK_CAP"] = 6000
        else:
            self.log("reasoning-posture", PASS, "no separate reasoning channel")
        # known thinking switches
        for extra in ({"chat_template_kwargs": {"enable_thinking": False}},
                      {"enable_thinking": False},
                      {"thinking": {"type": "disabled"}}):
            _, c2, d2 = self.chat(msgs, 100, extra=extra)
            if c2 == 200:
                self.log("thinking-switch", PASS, f"accepted {list(extra.keys())[0]}")
                self.reco["LLM_EXTRA_BODY"] = json.dumps(extra, ensure_ascii=False)
                self.think_extra = extra
                return
        self.log("thinking-switch", WARN, "no known thinking switch accepted")

    def step_budget(self):
        heavy = ("以下是2024年12个月的销售额(元): 1月 6223229.29, 2月 4841963.86, 3月 7099127.34, "
                 "4月 7387746.72, 5月 7061970.59, 6月 7224920.28, 7月 7483638.54, 8月 6918971.43, "
                 "9月 7829912.48, 10月 6290554.84, 11月 12314323.26, 12月 7078238.90。"
                 "请计算每个月的环比增长率(保留4位小数), 然后按增长率从高到低排序, 并说明最高和最低的月份。")
        msgs = [{"role": "user", "content": heavy}]
        worst = None
        for mx in (700, 2000, 6000):
            dt, code, d = self.chat(msgs, mx, extra=self.think_extra)
            if code != 200:
                self.log(f"budget-{mx}", FAIL, f"HTTP {code}")
                continue
            ch = d["choices"][0]
            m = ch.get("message", {})
            content = (m.get("content") or "").strip()
            used = d.get("usage", {}).get("completion_tokens")
            if not content and ch.get("finish_reason") == "length":
                self.log(f"budget-{mx}", WARN,
                         f"empty content with usage=={used} (thinking-loop signature)")
                worst = mx
            elif not content:
                self.log(f"budget-{mx}", FAIL, f"empty content, finish={ch.get('finish_reason')}")
                worst = mx
            else:
                self.log(f"budget-{mx}", PASS, f"content {len(content)} chars ({dt:.1f}s)")
        if worst:
            rec = {"700": 3000, "2000": 4500, "6000": 9000}.get(str(worst), 6000)
            self.reco["ANSWER_TOK"] = rec
            self.reco["LLM_TOK_CAP"] = rec
            self.log("budget-advice", WARN,
                     f"recommend ANSWER_TOK={rec} (+ empty-answer retry) — "
                     "see methodology §2.5.6 thinking-budget trap")

    def _qa_once(self, q):
        dt, code, d = self.chat([{"role": "user", "content": q}], 100, extra=self.think_extra)
        if code != 200:
            return "http"
        m = d["choices"][0].get("message", {})
        c = (m.get("content") or "").strip()
        return c if c else "empty"

    def step_concurrency(self):
        qs = ["中国的首都是哪里?", "水的化学式是什么?", "3乘以4等于几?", "太阳从哪边升起?"]
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(4) as ex:
            outs = list(ex.map(self._qa_once, qs))
        dt = time.time() - t0
        empty = sum(1 for o in outs if o in ("empty", "http"))
        if empty == 0 and dt < 4 * 2.0:
            self.log("concurrency-4", PASS, f"4 parallel in {dt:.1f}s, no empty")
        elif empty == 0:
            self.log("concurrency-4", WARN, f"{dt:.1f}s (serialized? use fewer workers)")
        else:
            self.log("concurrency-4", FAIL, f"{empty}/4 empty under concurrency")

    def step_damage(self, n=20):
        qs = ([f"{i}+{i}等于几? 只回答数字" for i in range(1, 11)] +
              ["中国的首都是哪里?", "水的化学式是什么?", "地球绕太阳转一圈多久?",
               "1到10的和是多少?", "光速大约是多少?", "HTTP是什么的缩写?",
               "斐波那契数列前两项是什么?", "一年有多少天?", "0除以1等于几?",
               "圆周率前三位是?"])
        empty, http = 0, 0
        with concurrent.futures.ThreadPoolExecutor(4) as ex:
            outs = list(ex.map(self._qa_once, qs[:n]))
        for o in outs:
            if o == "empty":
                empty += 1
            elif o == "http":
                http += 1
        rate = (empty + http) / n * 100
        if rate == 0:
            self.log("damage-test", PASS, f"{n} rapid QAs, 0 empty / 0 http")
        elif rate <= 5:
            self.log("damage-test", WARN, f"{rate:.0f}% empty — add empty-answer retry")
        else:
            self.log("damage-test", FAIL, f"{rate:.0f}% empty — fix deployment before benchmarking")

    # ---------- run ----------
    def run(self, full=False):
        print(f"probing {self.base} (model={self.model})\n")
        if not self.step_models():
            print("\nendpoint unreachable — aborting")
            return False
        self.step_qa()
        self.step_tools()
        self.step_reasoning()
        self.step_budget()
        self.step_concurrency()
        if full:
            self.step_damage()
        print("\n==== summary ====")
        counts = {PASS: 0, WARN: 0, FAIL: 0}
        for _, st, _ in self.report:
            counts[st] += 1
        print(f"PASS {counts[PASS]} | WARN {counts[WARN]} | FAIL {counts[FAIL]}")
        if counts[FAIL]:
            print("verdict: fix deployment failures BEFORE benchmarking "
                  "(a broken endpoint makes every score meaningless)")
        elif counts[WARN]:
            print("verdict: benchmarkable with the recommended settings below")
        else:
            print("verdict: healthy endpoint")
        print("\n==== recommended env ====")
        for k in ("ANSWER_TOK", "LLM_TOK_CAP", "LLM_EXTRA_BODY", "ANSWER_CTX"):
            print(f"export {k}={self.reco[k]}")
        print("note: ANSWER_CTX=1 (rich observation context) helps strong models but "
              "can hurt 4B-class models — A/B it on your error set first "
              "(see methodology §2.5.10-2.5.11).")
        return True


def main():
    ap = argparse.ArgumentParser(description="LLM endpoint deployment fingerprint probe")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model", default=None, help="model id (default: first from /models)")
    ap.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", "none"))
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--full", action="store_true", help="add 20-shot damage test")
    args = ap.parse_args()
    p = Probe(args.base_url, args.model, args.api_key, args.timeout)
    sys.exit(0 if p.run(full=args.full) else 1)


if __name__ == "__main__":
    main()
