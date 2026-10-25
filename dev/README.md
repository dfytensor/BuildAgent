# dev/ — 部署指纹探针与诊断脚本（过程档案）

> 这些不是正式评测 harness 的一部分，而是"**在跑 150 题之前，先确认部署是健康的**"所用的一次性探针与诊断脚本。
> 来自原始实验环境（Windows + 本地 llama.cpp / OpenRouter / DeepSeek 官方 API），路径与端口为当时示例。
> **所有密钥已移除**，请通过环境变量提供：`OPENROUTER_API_KEY` / `DEEPSEEK_API_KEY`。

## 为什么需要这一层

同一个模型换一个服务端，失败模式会变：空答、丢首 token、思考预算截断、429 限流、假崩溃……
如果不先做部署体检，就会把**服务缺陷误诊为模型缺陷**。方法论 §2.5.2 / §2.5.6 的结论都建立在这一层之上。

## 上线前 7 步探针（顺序执行）

| 步骤 | 目的 | 判别 |
|---|---|---|
| 1. `/v1/models` 或 `/health` | 服务是否活着、真实模型 ID | 200 + 非空列表 |
| 2. 基础 QA（1+1） | 连通性 / 空答 / 首 token 丢失 | content 非空且正确 |
| 3. 原生 function calling | 是否返回 `tool_calls`、参数是否合法 JSON | finish=tool_calls |
| 4. 思考姿态 | `reasoning_content` 是否存在、是否计入 completion | 记录 usage 结构 |
| 5. 预算探针（700 / 2000 / 6000） | **思考死循环**：content 是否始终为空、usage 是否恰好等于上限 | 空 content + usage=max → 病态 |
| 6. 并发探针（2/4 路） | 是否串行、是否并发空答 | 与单路对比延迟/内容 |
| 7. 损伤测试（20 连发） | 空答率 / 截断率 | 目标 0%；>5% 需修部署 |

**确定性答败签名**（本实验最重要的部署指纹）：
`HTTP 200 + content='' + usage.completion_tokens == max_tokens + reasoning_content 非空`
→ 思考吃满预算，正文没开始。修法：答案路径关思考（llama.cpp `chat_template_kwargs.enable_thinking=false`）或加大预算 + 空答重试。

## 五类部署陷阱速查

| 陷阱 | 表征 | 修法 |
|---|---|---|
| 服务端空答损伤 | ~20% 随机空 content，重试可恢复 | 修部署（bf16 修复版） |
| 429 双形态 | `free-models-per-day` vs `temporarily rate-limited upstream` | 前者等 UTC 日切/充值，后者换时段/模型 |
| key 限额 ≠ 账号日配额 | auth/key 显示剩余，但免费模型仍 429 | 以 429 文案为准 |
| 思考预算截断/死循环 | 见上"确定性答败签名" | 答案器关思考 / 6000 预算 / 空答重试 |
| worker"崩溃" | runner 报 `(worker崩溃)`，单题裸跑正常 | 退避×多次调用 > 900s 断头台；`CASE_TIMEOUT=1800` + stderr 落盘 |

## 目录

```
probes/
  t_or_probe.py, t_probe2.py, t_cands.py        OpenRouter 可用性/限流类型探测
  t_xingchen.py, t_xing_patience.py             免费模型窗口成功率探测
  t_8080.py, t_8080_b.py, t_8080_fix.py         本地 llama.cpp 部署体检 + 思考开关
  t_spark_modes.py, t_stable.py                 思考模式 / 稳定性
  t_ds_models.py, t_ds_probe.py                 DeepSeek 官方 API 行为
  t_damage.py, t_firsttoken.py                  空答损伤 / 首 token 测试
diagnostics/
  t_ds_fail_audit.py                            逐题失败解剖（题面/黄金/工具链/答案 + 跨模型对照）
  t_gold_check.py                               黄金答案/数据视图疑点查证
  t_improve_scan.py                             失败可干预性分类
  t_qm_usage.py                                 语义层实际调用率
  t_repro1.py, t_repro2.py, t_ds_l901*.py       确定性答败/提示病态的精确复现
  t_rep18_compare.py, t_spark_v11d_report.py    代表集与轮次分解报告
  t_tax.py, t_v11d_check.py, t_v11_1_values.py  口径/黄金修正的验证
patches/
  patch_v11b.py, patch_v11c.py, patch_v11_1.py  机制轮次的精确改动（可审计）
  patch_budget.py, patch_answertok.py           回答器预算
  patch_thinkoff.py, patch_emptyretry.py        思考姿态与空答重试
  patch_infra.py                                错误日志 + stderr 落盘
```

## 备注

- 脚本里的绝对路径（`F:\智能数据分析agent`、`C:\Users\...`）是原始环境示例；移植时请改为仓库根目录/`~`。
- 探针属于**过程文物**：保留原样便于复现当时的判断，不保证与新版本代码完全兼容。
