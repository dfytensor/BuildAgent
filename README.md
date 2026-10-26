# BuildAgent — 格物致知：用 150 题阶梯把数据分析 Agent 从 1B 测到强模型

> 一套**可复现、反作弊、带误差棒**的 Agent 能力评测与迭代方法：
> 固定一把尺子（150 道分层用例 + 确定性判分），在 **(模型 × 部署 × 脚手架 × 数据模型)** 四维空间里做单变量迭代，
> 每一分增量都能回答：**这是模型会的，还是工程/数据代做的？**

---

## 1. 最终结果（同尺 150 题，v1.1.1 修正评测）

| 模型 × 配置 | 工具OK | 执行OK | **最终答对** | SQL | pandas | tool |
|---|---|---|---|---|---|---|
| **deepseek-flash (V4.1-1017) + v12b**（`ANSWER_CTX=1`） | 99.3% | 86.0% | **99.3% (149/150)** | 100% | 100% | 98% |
| **spark-x2.6-4b-lossless（本地）+ v12**（数据治理） | 98.7% | 79.3% | **88.0% (132/150)** | 82% | 86% | 96% |

### 1.1 v1.0 冻结评测（官方历史阶梯）

| 模型 × 脚手架 | 最终答对 | 说明 |
|---|---|---|
| MiniCPM5-1B + v7（16 题抽样） | 25.0% | 未微调 1B 的真实语义天花板 |
| MiniCPM5-2B + v7 | 32.0% | 规模 +7pt |
| spark-x2.6-4b（本地）+ v9 | 56.7% | 4B 本地部署首次全量 |
| spark-x2.6-4b（本地）+ v11c | 65.3% | 语义层 v2 + 上下文工程 |
| minimax-m3.1-flash + v9 | 67.3% | 云端大模型参照 |
| deepseek-flash + v11c | 86.0% | 强模型 + 完整脚手架 |

> v1.0 与 v1.1 并列保留：v1.1 修正了 1 个黄金 bug、3 个缺少 ORDER BY 的题、10 个歧义题面（备份见 `eval/cases.v1.0.bak.json`）。**改题必须全模型复跑，不允许只报新分。**

---

## 2. 核心结论

1. **脚手架只能兑现能力，不能创造能力**：4B 从 v11d 76.7% → v12 88.0%（数据治理 +11.3pt），但对 DeepSeek 仍有 17 道纯语义差距（双错仅 1）。
2. **约束是双向的，越往下层越可靠**：`提示词 < 工具接口 < 数据模型 < 数据库约束`。4B 的 35 道失败里 14 道源于"把 v_sales 明细行当订单表"，补 `v_orders/v_customers/v_product_sales` 三张粒度视图后一次 +11.3pt。
3. **强模型的"最后一公里"通常不是智力**：DeepSeek 86% → 92%（跨轮上下文/口径）→ 99.3%（评测修正 + 观测选择），21 道失败里只有 ~4 道是真错。
4. **机制有效性随能力变号**：把"调用 SQL + 结果选择优先级"给回答器，DeepSeek +2pt，4B −2.7pt（提示更快撞上限，后段观测被截断）→ 做成 `ANSWER_CTX` 开关。
5. **混合路径（复杂 SQL→pandas）对 4B 无效**：强制 PANDAS 采纳率 89% 时只做出 4/18 错题（SQL 直答对照 2/18）——瓶颈是语义推理，不是 SQL 路径。

---

## 3. 实验过程（单变量迭代账本）

| 版本 | 引入 | 结果 | 解决 / 暴露 |
|---|---|---|---|
| v0_bare | 裸模型 | 2.0% | 编造数据 / 只给 SQL 文本 |
| v1_react | 文本 ReAct + SQL | 2.0% | 格式漂移 / 表列名幻觉 |
| v2_schema | schema 注入 | 4.0% | 提示变长导致协议崩塌 |
| v3_selfheal | few-shot + 纠偏 | 1.3% | 1B 多约束互相挤压 |
| v4_sandbox | **微步分解 + 原生 function calling + 沙盒** | 4.0% | 执行率破零 |
| v5_memory | 事实卡记忆 + 溯源 | 4.0% | 长对话不溢出 |
| v6_router | 路由 + 模板/正则 | 14.0% | **约 9 分是"助考"，触发去作弊重迭代** |
| v7_general | 去作弊终态 | 8.7% | 协议 90.7%，语义天花板显形 |
| v8_calculator | 确定性算术 | 负收益 | 失败发生在算术之前 |
| v9_scaffold | 行限 / schema 直答 / 语义约定 / 轮次 5 | minimax SQL +22pt | 差分诊断的精度 |
| v10_metric | 语义层（口径注册表） | +8.7pt（消融） | 口径/粒度错误有了确定性兜底 |
| v11a-d | 呈现层 / 空结果诊断 / 语义层 v2 / 跨轮上下文 | DeepSeek 86→92% | 失败解剖见 §2.5.9 |
| v1.1 eval | 1 黄金 bug + 3 ORDER BY + 10 歧义 | DeepSeek → 99.3% | **评测质量决定测量上限** |
| **v12_views** | **三张粒度视图 + 数据源地图 + avg_list_price** | **4B 76.7→88.0%** | 数据治理成为第二套脚手架 |
| v12b_select | 调用 SQL 入上下文 + 选结果优先级 | DS +2pt / 4B −2.7pt | 机制×能力交互 → `ANSWER_CTX` 开关 |
| v13b/c/d | load_df + 路由 / 硬门禁 / 强制 PANDAS | 6 / 7 / 4 of 18 | **负结果**：语义瓶颈不是 SQL 路径 |

完整叙事、部署指纹、四象限分析、失败解剖见 [`docs/methodology.md`](docs/methodology.md)。

---

## 4. 仓库结构

```
agent/                  12 代 Agent 继承链（v0→v13）+ 工具层
  common.py             LLM 客户端 / sqlite / 沙盒 / make_chart / calculator / 结果呈现 / load_df
  query_metric.py       语义层：指标注册表 + 实体级 Top-N 排名 + avg_list_price
  base_agent.py         会话 / 事实卡 / trace / 工具分发
  v4_sandbox.py         两段式微任务（规划器/回答器）+ 工具协议 + ANSWER_CTX
  v5_memory.py          事实卡（问答对）+ 溯源
  v7_general.py         去作弊终态
  v9_scaffold.py        脚手架优化
  v10_metric.py         语义层接入
  v11_present/diag/metric2/context.py   v11 四轮
  v12_views.py          数据治理（v_orders 等）
  v12b_select.py        多观测选择
  v13_hybrid/hybrid2/gated/forced.py   混合路径试验（负结果）
data/
  make_data.py          确定性造数（seed=42）
  add_views.py          宽表视图：v_sales / v_orders / v_customers / v_product_sales
  shop.db               生成好的电商库（可直接用）
eval/
  cases.json            150 题 + 黄金答案（v1.1.1）
  cases.v1.0.bak.json   冻结的 v1.0 题集备份
  runner.py             评测运行器（子进程隔离/超时/续跑/自动归档）
  checker.py            判分器（数值容差/单位等价/图表 mtime）
  overlap.py            四象限重叠分析
  round_report.py       轮次对比报告（修好/弄坏/失败分类）
  audit_arm.py          单臂质量审计（基建标记/分层表）
  merge_layers.py       多批次合并
  verify_goldens.py     黄金答案执行审计
  results/              逐题快照 + 68 份归档（archive/）
docs/methodology.md     方法论全文
dev/                    部署指纹探针 / 诊断脚本 / 机制补丁（过程档案，密钥已清洗）
  README.md             7 步部署体检流程 + 五类陷阱速查
  probes/               OpenRouter / 本地 llama.cpp / DeepSeek 行为探针
  diagnostics/          失败解剖、黄金查证、口径验证、轮次分解、混合路径报告
  patches/              v11/v12 各机制轮次的精确改动
```

---

## 5. 复现

```bash
# 1) 环境
python -m venv .venv
.venv/Scripts/pip install openai pandas matplotlib numpy

# 2) 数据（seed=42 确定性；仓库已带 shop.db + 全部视图，可跳过）
python data/make_data.py
python data/add_views.py

# 3) 选一个后端（示例：DeepSeek 官方 API，强模型配置）
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-flash
export LLM_API_KEY=sk-...            # 只放环境变量，不要提交
export LLM_EXTRA_BODY='{}'
export LLM_TOK_CAP=6000
export ANSWER_TOK=6000
export ANSWER_CTX=1                  # 强模型：观测上下文 + 选结果优先级
export CASE_TIMEOUT=1800

# 4) 全量 150 题（子进程隔离 + 4 并发）
python eval/runner.py --agent v12b_select --suite all --subprocess --workers 4

# 5) 分析
python eval/round_report.py eval/results/<prev>.json eval/results/<cur>.json prev cur
python eval/overlap.py --a <A>.json --b <B>.json --la A --lb B      # 路径相对 eval/results
python eval/audit_arm.py eval/results/<cur>.json
```

**本地 llama.cpp（spark-x2.6-4b，4B 配置）**：`LLM_BASE_URL=http://127.0.0.1:8080/v1`，
`LLM_MODEL=spark-x2.6-4b-lossless`，`LLM_EXTRA_BODY='{"chat_template_kwargs": {"enable_thinking": false}}'`（答案器关思考，规划器保持思考），`ANSWER_TOK=3000`，**不要设 `ANSWER_CTX`**。

---

## 6. 关键结果文件

| 文件 | 含义 |
|---|---|
| `eval/results/deepseek_v12b_full.json` | DeepSeek v12b × v1.1.1：149/150（99.3%） |
| `eval/results/v12_views_all.json` | spark-4B v12 × v1.1.1：132/150（88.0%） |
| `eval/results/deepseek_v12_full.json` | DeepSeek v12：146/150（97.3%） |
| `eval/results/v12b_select_all.json` | spark-4B v12b：128/150（85.3%） |
| `eval/results/v11d_v11_full.json` | DeepSeek v11d × v1.1：149/150 |
| `eval/results/v11d_context_all.json` | spark-4B v11d × v1.1：115/150（76.7%） |
| `eval/results/archive/` | 68 份逐题归档（每代模型/每个实验臂） |
| `eval/results/overlap_*.json` | 四象限差分（思维姿态/语义层/跨模型/数据治理） |

---

## 7. 诚实声明

- **单臂误差棒 ±2.8pt（1σ）**：k=3 分层抽样翻转率 14%；净差 <6pt 不称机制收益。
- **v1.0 有 8 道题没有唯一正确答案**（1 黄金 bug + 3 无 ORDER BY + 4 题面歧义），已在 v1.1 修正并单列；v1.1.1 补了 2 处"件/款"澄清。
- **模型部署指纹**：不同服务端会出现空答损伤、思考预算截断、429 双形态、假崩溃；换部署必须全量复测。
- **混合路径是负结果**：强制 PANDAS 采纳率 89% 也只做出 4/18 错题——4B 的瓶颈是语义，不是 SQL 路径。
- **顺手修复的真实 bug**：`tool_run_python` 从未把 `_ns_file/keep_ns` 传给子进程，"有状态沙盒"此前是失效的；`load_df` 让该问题暴露并修复。
- **反作弊三红线**：提示词/few-shot 不与题库撞车；不对题面写正则/模板直答；判分不依赖会话外残留状态。

MIT License.
