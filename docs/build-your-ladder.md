# Build Your Own Ladder in One Day

A step-by-step guide to applying the **格物致知 (Gewu-Zhizhi)** methodology — a fixed-ruler,
single-variable, anti-cheating evaluation loop — to any domain where an LLM agent must
answer questions over structured data.

The running example is a "data-analysis agent over a SQLite database", but the schema,
checker and workflow are domain-agnostic.

---

## 0. The rules you must not break (anti-cheating red lines)

1. **Prompts/few-shots must never collide with eval cases.** If a scaffold mechanism only
   works because it was shaped around a specific question, it is *invigilator engineering*,
   not capability.
2. **Never write per-question regex/templates in the scaffold.**
3. **Scoring must not depend on state outside the session.**
4. **When you discover an eval defect, fix it and re-run ALL models.** Keep both score
   versions (v1.0 frozen + v1.1 corrected) side by side.

---

## 1. Hours 1–2: define the domain and the ladder shape

Pick 6–10 **operation types** in your domain and spread them over difficulty levels:

```
L1  single-table, single operator          (count / sum / avg)
L2  list + format                          (top-N, "give me the first 5")
L3  filters + grouping                     (by category / month)
L4  multi-condition                        (range + category + channel)
L5  joins / cross-table                    (orders -> customers -> cities)
L6  dedup + ordering semantics             ("first 15 by id")
L7  multi-step arithmetic on query results (shares, per-capita)
L8  list with join + filters               (date/customer/channel columns)
L9  monthly/time aggregations
T1-T6  tool-protocol suite                 (same ladder but exercising tools/charts/multi-turn)
```

Rules of thumb:
- 50–150 questions is enough. 20 well-audited questions beat 500 sloppy ones.
- Every question must have a **deterministic, machine-checkable gold answer**.
- Include a few **multi-turn chains** ("remember this number", "now divide it") — they
  expose cross-turn weaknesses that single questions hide.

---

## 2. Hours 3–4: write cases + gold

Case schema (see `templates/cases.example.json`):

```json
{
  "id": "SQL-L5-02",
  "suite": "sql",
  "level": 5,
  "q": "List the name and city of customers in Shanghai (first 10)",
  "gold": {
    "kind": "values",
    "values": ["用户0005", "上海", "..."],
    "ref_sql": "SELECT c.name, c.city FROM customers c WHERE c.city='上海' ORDER BY c.id LIMIT 10"
  },
  "min_calls": 1,
  "need_tools": ["sql"]
}
```

**Gold rules (each one came from a real defect we shipped and had to fix):**

1. **Deterministic.** If the answer is a list, the ordering must be specified *in the
   question* and *in the ref* (`ORDER BY id LIMIT 15`). A `LIMIT` without `ORDER BY`
   makes the gold an arbitrary sample — we shipped 3 such defects (§2.5.9).
2. **Unambiguous.** "average product price" is ambiguous (list price vs transaction
   price). Clarify the wording; keep both readings documented. We shipped 4 such cases;
   four different models all answered the same "wrong" value — that is an eval defect,
   not a model failure.
3. **Consistent metric semantics across cases.** If "sales" means `status='completed'`
   in 90% of cases, do not silently use all-statuses in one case. Metric conventions
   belong in the **semantic layer** (`query_metric`), not scattered across golds.
4. **Audit the gold by executing every `ref_sql`/`ref_py`** (`verify_goldens.py`).
   Executability ≠ correctness: one of our golds returned a constant `100` for every
   channel because the denominator subquery repeated the channel filter.

---

## 3. Hour 5: bare-model baseline + damage control

Before any scaffold work:

```bash
python eval/runner.py --agent bare --suite all --subprocess --workers 2
```

- Expect single digits. This is your defect inventory, not a humiliation metric.
- **Probe the deployment first** (`probe/probe.py`): a broken endpoint
  (empty answers, thinking-budget loops, concurrency failures) will make every score
  meaningless. Fix deployment, then re-run — we once attributed service bugs to the model
  for a whole iteration (§2.5.2).
- **Quantify noise**: re-run a stratified sample 3× and measure the flip rate. Our flip
  rate was 14% → ±2.8pt (1σ) on 150 questions. Any mechanism claim below ~6pt is noise.

---

## 4. Hours 6–8: single-variable scaffold iterations

One mechanism per iteration, full re-run, archive everything:

| Layer | Mechanisms that worked for us |
|---|---|
| Protocol | micro-task split (planner/answerer), native function calling, lenient parsing |
| Memory | fact cards storing **Q+A pairs** (answer numbers survive cross-turn) |
| Semantics | metric registry (`query_metric`) — conventions in code, not in the prompt |
| Data model | grain views (`v_orders` one-row-per-order) — duplicates become impossible |
| Answering | list-completeness rule, result-selection priority, empty-answer retry |

Ledger discipline: for every iteration record **fixed / broken** counts and classify.
Mechanisms that help strong models can hurt small ones (our `ANSWER_CTX` was +2pt for
DeepSeek, −2.7pt for the 4B) — make them configurable, not universal.

---

## 5. Ongoing: dual-track eval + negative-result ledger

- Freeze eval versions. Clarifications and gold fixes go into the next version, and
  **all models are re-run on the changed cases**.
- Keep a **negative-result ledger** (we have v8, v13 as permanent entries). Negative
  results are what make the positive claims believable — and they save the next person
  from repeating the experiment.
- Score attribution: every point should be labeled **model / scaffold / data-model / eval**.
  "The agent scored 99%" is meaningless without that breakdown.

---

## 6. What a finished ladder looks like

- `eval/cases.json` — questions + golds + refs
- `eval/verify_goldens.py` — executes every ref, flags ambiguity
- `eval/runner.py` — subprocess-isolated, resumable, auto-archiving
- `eval/checker.py` — numeric tolerance + text containment + artifact checks
- `eval/results/archive/` — one JSON per (model × version) run, forever
- `eval/round_report.py` + `eval/overlap.py` — fixed/broken quadrants between any two runs
- A written **failure anatomy** for the current champion, split into:
  eval defects / metric convention / scaffold assembly / real capability

See this repo's `eval/` for a working reference implementation.
