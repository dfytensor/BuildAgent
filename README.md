# BuildAgent — 格物致知：用 150 题阶梯把数据分析 Agent 从 1B 测到强模型

> 一套**可复现、反作弊、带误差棒**的 Agent 能力评测与迭代方法：
> 固定一把尺子（150 道分层用例 + 确定性判分），在 **(模型 × 部署 × 脚手架)** 三维空间里做单变量迭代，
> 每一分增量都能回答：**这是模型会的，还是工程代做的？**

---

## 1. 最终结果（同尺 150 题）

### 1.1 v1.1 修正评测（当前版本）

| 模型 × 脚手架 | 工具OK | 执行OK | **最终答对** | SQL | pandas | tool |
|---|---|---|---|---|---|---|
| **deepseek-flash (V4.1-1017) + v11d** | 100% | 93.3% | **99.3% (149/150)** | 100% | 98% | 100% |
| **spark-x2.6-4b-lossless（本地 llama.cpp）+ v11d** | 99.3% | 80.0% | **76.7% (115/150)** | 66% | 82% | 82% |

### 1.2 v1.0 冻结评测（官方阶梯，历史对照）

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

## 2. 四个核心结论

1. **脚手架只能兑现能力，不能创造能力**：4B 本地 65.3% → 76.7%（+11.4pt：评测账 +8、脚手架账 +9），但对 DeepSeek 仍有 34 道纯语义差距（双错仅 1 题）。
2. **强模型的“最后一公里”通常不是智力**：DeepSeek 86% → 92%（跨轮上下文/口径）→ 99.3%（评测修正），21 道失败里只有 ~4 道是真错。
3. **口径必须沉入代码**：语义层 `query_metric` 消融 **+8.7pt**（19 独对 / 6 独错）；但刚性口径也有 4% 反噬，需记账。
4. **部署本身是被测系统的一部分**：思考预算截断、空答损伤、429 双形态、worker 假崩溃——换部署必须全量复测，否则会把服务缺陷误诊为模型缺陷。

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
| v6_router | 路由 + 模板/正则 | 14.0% | **约 9 分是“助考”，触发去作弊重迭代** |
| v7_general | 去作弊终态 | 8.7% | 协议 90.7%，语义天花板显形 |
| v8_calculator | 确定性算术 | 负收益 | 失败发生在算术之前 |
| v9_scaffold | 行限/ schema 直答 / 语义约定 / 轮次 5 | minimax SQL +22pt | 差分诊断的精度 |
| v10_metric | 语义层（口径注册表） | +8.7pt（消融） | 口径/粒度错误有了确定性兜底 |
| v11a-d | 呈现层 / 空结果诊断 / 语义层 v2 / 跨轮上下文 | DeepSeek 86→92% | 失败解剖见 §2.5.9 |
| v1.1 eval | 1 黄金 bug + 3 ORDER BY + 10 歧义 | DeepSeek → 99.3% | **评测质量决定测量上限** |

完整叙事、部署指纹、四象限分析、失败解剖见 [`docs/methodology.md`](docs/methodology.md)。

---

## 4. 仓库结构

```
agent/                  12 代 Agent 继承链（v0→v11d）+ 工具层
  common.py             LLM 客户端 / sqlite / 沙盒 / make_chart / calculator / 结果呈现
  query_metric.py       语义层：指标注册表 + 实体级 Top-N 排名
  base_agent.py         会话 / 事实卡 / trace
  v4_sandbox.py         两段式微任务（规划器/回答器）+ 工具协议
  v5_memory.py          事实卡（问答对）+ 溯源
  v7_general.py         去作弊终态
  v9_scaffold.py        脚手架优化
  v10_metric.py         语义层接入
  v11_present.py        v11a 呈现层
  v11_diag.py           v11b 空结果诊断
  v11_metric2.py        v11c 语义层 v2
  v11d_context.py       v11d 跨轮上下文/口径
data/
  make_data.py          确定性造数（seed=42）
  add_views.py          宽表视图 v_sales（LEFT JOIN）
  shop.db               生成好的电商库（可直接用）
eval/
  cases.json            150 题 + 黄金答案（v1.1）
  cases.v1.0.bak.json   冻结的 v1.0 题集备份
  runner.py             评测运行器（子进程隔离/超时/续跑/自动归档）
  checker.py            判分器（数值容差/单位等价/图表 mtime）
  overlap.py            四象限重叠分析
  round_report.py       轮次对比报告（修好/弄坏/失败分类）
  audit_arm.py          单臂质量审计（基建标记/分层表）
  merge_layers.py       多批次合并
  verify_goldens.py     黄金答案执行审计
  results/              逐题快照 + 56 份归档（archive/）
docs/methodology.md     方法论全文
dev/                    部署指纹探针 / 诊断脚本 / 机制补丁（过程档案，密钥已清洗）
  README.md             7 步部署体检流程 + 五类陷阱速查
  probes/               OpenRouter / 本地 llama.cpp / DeepSeek 行为探针
  diagnostics/          失败解剖、黄金查证、口径验证、轮次分解
  patches/              v11 各机制轮次的精确改动
```

---

## 5. 复现

```bash
# 1) 环境
python -m venv .venv
.venv/Scripts/pip install openai pandas matplotlib numpy

# 2) 数据（seed=42 确定性；仓库已带 shop.db，可跳过）
python data/make_data.py
python data/add_views.py

# 3) 选一个后端（示例：DeepSeek 官方 API）
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-flash
export LLM_API_KEY=sk-...            # 只放环境变量，不要提交
export LLM_EXTRA_BODY='{}'
export LLM_TOK_CAP=6000
export ANSWER_TOK=6000
export CASE_TIMEOUT=1800

# 4) 全量 150 题（子进程隔离 + 4 并发）
python eval/runner.py --agent v11d_context --suite all --subprocess --workers 4

# 5) 分析
python eval/round_report.py eval/results/<prev>.json eval/results/v11d_context_all.json prev cur
python eval/overlap.py --a <A>.json --b <B>.json --la A --lb B      # 路径相对 eval/results
python eval/audit_arm.py eval/results/v11d_context_all.json
```

**本地 llama.cpp（spark-x2.6-4b）**：`LLM_BASE_URL=http://127.0.0.1:8080/v1`，
`LLM_MODEL=spark-x2.6-4b-lossless`，`LLM_EXTRA_BODY='{"chat_template_kwargs": {"enable_thinking": false}}'`（答案器关思考，规划器保持思考），`ANSWER_TOK=3000`。

---

## 6. 关键结果文件

| 文件 | 含义 |
|---|---|
| `eval/results/v11d_v11_full.json` | DeepSeek v11d × v1.1：149/150（99.3%） |
| `eval/results/v11d_context_all.json` | spark-4B v11d × v1.1：115/150（76.7%） |
| `eval/results/v11d_v10_full.json` | DeepSeek v11d × v1.0：138/150（92.0%） |
| `eval/results/deepseek_full_merged.json` | DeepSeek v11c × v1.0：129/150（86.0%） |
| `eval/results/v11c_full.json` | spark-4B v11c × v1.0：98/150（65.3%） |
| `eval/results/archive/` | 56 份逐题归档（每代模型/每个实验臂） |
| `eval/results/overlap_*.json` | 四象限差分（思维姿态/语义层/跨模型） |

---

## 7. 诚实声明

- **单臂误差棒 ±2.8pt（1σ）**：k=3 分层抽样翻转率 14%；净差 <6pt 不称机制收益。
- **v1.0 有 8 道题没有唯一正确答案**（1 黄金 bug + 3 无 ORDER BY + 4 题面歧义），已在 v1.1 修正并单列。
- **模型部署指纹**：不同服务端会出现空答损伤、思考预算截断、429 双形态、假崩溃；所有对照均在健康部署上完成。
- **反作弊三红线**：提示词/few-shot 不与题库撞车；不对题面写正则/模板直答；判分不依赖会话外残留状态。

MIT License.
