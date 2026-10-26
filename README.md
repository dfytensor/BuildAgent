# BuildAgent — Gewu-Zhizhi: benchmarking a data-analysis agent from a 1B to a frontier model

> A **reproducible, anti-cheating, error-barred** evaluation and iteration methodology:
> keep one fixed ruler (a 150-question stratified ladder + deterministic scoring) and run
> single-variable iterations across **(model × deployment × scaffold × data model)**.
> Every point of improvement can answer: *is this the model, the scaffold, the data model,
> or the eval?*

[中文说明 / Chinese docs](README.zh-CN.md) · [Methodology (Chinese, full)](docs/methodology.md) · [Build your own ladder in one day](docs/build-your-ladder.md)

---

## 1. Final results (150 questions, v1.1.1 corrected eval)

| Model × config | tool OK | exec OK | **final correct** | SQL | pandas | tool |
|---|---|---|---|---|---|---|
| **deepseek-flash (V4.1-1017) + v12b** (`ANSWER_CTX=1`) | 99.3% | 86.0% | **99.3% (149/150)** | 100% | 100% | 98% |
| **spark-x2.6-4b-lossless (local llama.cpp) + v12** | 98.7% | 79.3% | **88.0% (132/150)** | 82% | 86% | 96% |

### 1.1 Frozen v1.0 ladder (historical baseline)

| Model × scaffold | final correct | note |
|---|---|---|
| MiniCPM5-1B + v7 (16-q sample) | 25.0% | untuned 1B semantic ceiling |
| MiniCPM5-2B + v7 | 32.0% | scale +7pt |
| spark-x2.6-4b (local) + v9 | 56.7% | first full 4B run |
| spark-x2.6-4b (local) + v11c | 65.3% | semantic layer v2 + context engineering |
| minimax-m3.1-flash + v9 | 67.3% | cloud frontier reference |
| deepseek-flash + v11c | 86.0% | frontier model + full scaffold |

> v1.0 and v1.1 are kept side by side. v1.1 fixed 1 gold bug, 3 missing `ORDER BY` questions
> and 10 ambiguous wordings (backup: `eval/cases.v1.0.bak.json`). **Changing the eval requires
> re-running every model — new scores only, never silently.**

---

## 2. Five takeaways

1. **Scaffolds realize capability; they don't create it.** The 4B went 65.3% → 88.0% via
   data governance, but 17 pure-semantic gaps vs DeepSeek remain (only 1 shared failure).
2. **Constraints work better lower in the stack**: `prompt < tool interface < data model`.
   Adding three grain views (`v_orders`, `v_customers`, `v_product_sales`) was worth
   +11.3pt for the 4B — no prompt engineering could do that.
3. **The frontier model's last mile is rarely intelligence**: DeepSeek 86% → 92%
   (cross-turn context, metric conventions) → 99.3% (eval corrections + observation
   selection). Of 21 failures only ~4 were real model errors.
4. **Mechanism effectiveness flips with model capability**: enriching the answerer's
   observation context was **+2pt for DeepSeek, −2.7pt for the 4B** (prompt-budget
   truncation). Ship it behind a switch (`ANSWER_CTX`).
5. **Hybrid "SQL→pandas" is a negative result at 4B**: forcing the pandas path with 89%
   adoption solved 4/18 hard questions (SQL control: 2/18) — the bottleneck is semantic
   reasoning, not the SQL dialect.
6. **The methodology transfers across domains**: on a second domain (hospital clinic,
   66-question ladder rebuilt from scratch), data governance took DeepSeek from a
   cold-start 15.2% to **37.9% (+22.7pt, 15 fixed / 0 broken)** — and the ladder was
   built with **zero eval defects** on the first pass (the v1.1 discipline moved into
   the builder).

### 2.5 Second-domain validation (hospital clinic, 66 questions)

Same-structure mapping: visits↔orders, prescriptions↔order_items, patients↔customers,
insurance↔channel, no-prescription visits (17%) ↔ empty-detail orders (8%). Grain traps
(duplicate lines / empty header rows / count-vs-kind ambiguity) exist by design.

| config (DeepSeek, full runs) | score | note |
|---|---|---|
| v9h baseline (schema + conventions, no data-source map / no metric tool / views unmentioned) | 15.2% (10/66) | SQL exec 0%, cold start |
| v12h governed (3 grain views + data-source map + `hosp_metric`) | **37.9% (25/66)** | **+22.7pt, 15 fixed / 0 broken** |

Reproducibility: two independent executions scored 15.2/15.4 and 37.9/37.9.
Remaining 41 failures: 31 semantic + 9 no-tool-call + 1 missing-info (exec only 21-25% —
date-substr conventions and joins are still hard for everyone).

---

## 3. The iteration ledger (single-variable, archived)

| version | mechanism | score | resolved / exposed |
|---|---|---|---|
| v0_bare | bare model | 2.0% | hallucination / no tool use |
| v1-v3 | ReAct + schema + self-heal | 1.3-4.0% | protocol collapse under multi-constraints |
| v4_sandbox | micro-task split + native tools + sandbox | 4.0% | execution breaks zero |
| v5_memory | fact cards + trace | 4.0% | long-dialog overflow |
| v6_router | router + templates/regex | 14.0% | **~9pt was invigilator engineering → de-cheat** |
| v7_general | de-cheated final | 8.7% | protocol 90.7%, semantic ceiling exposed |
| v8_calculator | deterministic arithmetic | negative | failure happens before arithmetic |
| v9_scaffold | limits / schema probe / conventions / rounds 5 | minimax SQL +22pt | precision of diff diagnosis |
| v10_metric | semantic layer (metric registry) | +8.7pt ablation | conventions live in code |
| v11a-d | presentation / empty-retry / semantic v2 / context | DeepSeek 86→92% | failure anatomy §2.5.9 |
| **v1.1 eval** | 1 gold bug + 3 ORDER BY + 10 ambiguities | DeepSeek → 99.3% | **eval quality caps measurement** |
| **v12_views** | 3 grain views + data-source map | 4B 76.7→88.0% | data governance = 2nd scaffold |
| v12b_select | call-SQL context + selection priority | DS +2 / 4B −2.7 | mechanism × capability → `ANSWER_CTX` switch |
| v13b/c/d | load_df + router / hard gate / forced PANDAS | 6 / 7 / 4 of 18 | **negative result**: semantic, not path |

---

## 4. Repository layout

```
agent/                  12-generation agent chain (v0→v13) + tool layer
  common.py             client / sqlite / sandbox / make_chart / calculator / summarize / load_df
  query_metric.py       semantic layer: metric registry + entity Top-N + avg_list_price
  base_agent.py         session / fact cards / trace / dispatch
  v4_sandbox.py         two-phase micro-task (planner/answerer) + ANSWER_CTX switch
  v5_memory.py          fact cards (Q+A pairs) + trace
  v7_general.py         de-cheated reference
  v9_scaffold.py        scaffold tuning
  v10_metric.py         semantic layer hookup
  v11_*.py              presentation / diag / semantic-v2 / context rounds
  v12_views.py          data governance (grain views)
  v12b_select.py        observation selection
  v13_*.py              hybrid-path experiments (negative result)
  domain_hospital.py    hospital domain config (schema/prompt/tools + hosp_metric)
  v9h_baseline.py       hospital baseline agent (no governance)
  v12h_hospital.py      hospital governed agent
data/
  make_data.py          deterministic data (seed=42)
  add_views.py          grain views: v_sales / v_orders / v_customers / v_product_sales
  shop.db               ready-to-use SQLite DB
  make_hospital.py      second-domain (hospital clinic) deterministic data
  add_views_hospital.py hospital grain views: v_rx / v_visits / v_patients / v_drugs
  hospital.db           ready-to-use hospital DB (66-question second-domain eval)
eval/
  cases.json            150 questions + golds (v1.1.1)
  cases.v1.0.bak.json   frozen v1.0 backup
  runner.py             subprocess-isolated / resumable / auto-archiving runner
  checker.py            numeric tolerance + containment + artifact checks
  overlap.py            quadrant analysis between any two runs
  round_report.py       fixed/broken + failure taxonomy between two runs
  audit_arm.py          per-arm quality audit (infra markers / level table)
  verify_goldens.py     executes every gold ref
  build_cases_hospital.py  second-domain ladder builder (66 questions, audit built-in)
  cases_hospital.json   hospital ladder + golds (v1.0-fresh, zero build defects)
  results/              per-question snapshots + 71 archives
docs/
  methodology.md        full methodology (Chinese, 48KB)
  build-your-ladder.md  **build your own ladder in one day** (English)
templates/
  cases.example.json    case schema example
probe/
  probe.py              7-step deployment fingerprint CLI
dev/                    probes / diagnostics / patches (process archive, keys scrubbed)
```

---

## 5. Quickstart

```bash
# 1) environment
python -m venv .venv
.venv/Scripts/pip install requests openai pandas matplotlib numpy

# 2) data (deterministic seed=42; shop.db + views are already committed)
python data/make_data.py
python data/add_views.py

# 3) probe the deployment FIRST (60 seconds — never benchmark a broken endpoint)
python probe/probe.py --base-url https://api.deepseek.com/v1 \
                      --model deepseek-flash --api-key $LLM_API_KEY --full

# 4) run the full 150 (example: DeepSeek, strong-model config)
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-flash
export LLM_API_KEY=sk-...          # env only — never commit keys
export LLM_EXTRA_BODY='{}'
export LLM_TOK_CAP=6000
export ANSWER_TOK=6000
export ANSWER_CTX=1                # rich observation context (strong models)
export CASE_TIMEOUT=1800
python eval/runner.py --agent v12b_select --suite all --subprocess --workers 4

# 5) analyze
python eval/round_report.py eval/results/<prev>.json eval/results/<cur>.json prev cur
python eval/overlap.py --a <A>.json --b <B>.json --la A --lb B
python eval/audit_arm.py eval/results/<cur>.json
```

**Local llama.cpp (spark-x2.6-4b, 4B config)**: `LLM_BASE_URL=http://127.0.0.1:8080/v1`,
`LLM_MODEL=spark-x2.6-4b-lossless`,
`LLM_EXTRA_BODY='{"chat_template_kwargs": {"enable_thinking": false}}'` (answerer thinking
off, planner thinking on), `ANSWER_TOK=3000`, **no `ANSWER_CTX`**.

---

## 6. Key result files

| file | meaning |
|---|---|
| `eval/results/deepseek_v12b_full.json` | DeepSeek v12b × v1.1.1: 149/150 (99.3%) |
| `eval/results/v9h_hospital_full.json` | DeepSeek v9h baseline × hospital v1.0: 10/66 (15.2%) |
| `eval/results/v12h_hospital_full.json` | DeepSeek v12h governed × hospital v1.0: 25/66 (37.9%, **+22.7pt**) |
| `eval/results/v12_views_all.json` | spark-4B v12 × v1.1.1: 132/150 (88.0%) |
| `eval/results/deepseek_v12_full.json` | DeepSeek v12 × v1.1.1: 146/150 (97.3%) |
| `eval/results/v12b_select_all.json` | spark-4B v12b: 128/150 (85.3%) |
| `eval/results/v11d_v11_full.json` | DeepSeek v11d × v1.1: 149/150 |
| `eval/results/v11d_context_all.json` | spark-4B v11d × v1.1: 115/150 (76.7%) |
| `eval/results/archive/` | 68 per-question archives (every model × every experiment arm) |
| `eval/results/overlap_*.json` | quadrant diffs (thinking posture / semantic layer / cross-model / data governance) |

---

## 7. Honest declarations

- **Single-arm error bar ±2.8pt (1σ)**: k=3 flip rate 14% on 150 questions; treat
  differences <6pt as noise. Never claim a mechanism from a smaller delta.
- **v1.0 had 8 questions with no unique correct answer** (1 gold bug + 3 missing ORDER BY +
  4 ambiguities). Fixed in v1.1; v1.1.1 added two 件/款 clarifications. Both versions kept.
- **Deployment fingerprints are real**: thinking-budget loops, empty-answer damage, dual 429
  forms, fake worker crashes. `probe/probe.py` exists because we mis-attributed service bugs
  to models more than once.
- **The hybrid path is a documented negative result**: forced PANDAS with 89% adoption
  solved 4/18 hard questions vs 2/18 SQL control.
- **A real bug was found by this methodology**: the sandbox never persisted its namespace
  (`_ns_file/keep_ns` was dropped before reaching the child process) — the "stateful
  sandbox" had been silently stateless until `load_df` exposed it.
- **Anti-cheating red lines**: prompts/few-shots never collide with eval cases; no
  per-question regex/templates in the scaffold; scoring never depends on out-of-session state.

MIT License.
