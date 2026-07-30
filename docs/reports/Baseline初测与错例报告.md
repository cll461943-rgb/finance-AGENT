# Baseline 初测与错例报告

日期：2026-07-30。口径：契约 Smoke，不是正式 Baseline 横向实验。

## 1. 可报告结果

| 项目 | 结果 |
|---|---|
| 自动化测试 | 13 passed |
| EvidenceRecord 校验 | 128/128 |
| Smoke 问题 | 2025 年 9 月全国各地区原保险保费收入合计 |
| Top-1 Evidence | `DOC-032-2ddfb401b298-CELL-001` |
| 位置 | `各地区数据（月度）!C4` |
| 输出值 | 52145.77 亿元 |
| 引用 | 有 |
| Evidence Gate | warning：auto_checked |
| LLM Token / 成本 | 0 / 0 |

当前结果只证明统一入口能读取 EvidenceStore、返回统一 Answer/Trace 并失败关闭；不能据此报告 Recall@K、答案准确率或四方法优劣。

## 2. 方法状态

| 方法 | 状态 | 缺口 |
|---|---|---|
| Hybrid | BLOCK | 无统一适配器、BGE-M3/RRF/Reranker 运行与 20 题日志 |
| FinSage-Adapted | BLOCK | 无多路径检索适配与运行日志 |
| RegulatoryRAG-ML-Adapted | BLOCK | 无监管特征、Score Filter、引用/拒答日志 |
| HiREC-Lite | BLOCK | 无分层检索、完整性判断和单次补查 Trace |

## 3. 已发现错例与数据风险

- 16 条样例证据的单位为 `亿元、%`，金额与增长率无法直接区分。
- 示例文件标题含 2025 年 9 月，但部分 `table_semantics.period` 只有 `2025`，月份粒度丢失。
- 同一年度部分 Header Path 未继承年份。
- 3 份旧版 DOC 只能结构探测，版面和表格语义需人工核验。
- 当前证据状态为 `auto_checked`，没有人工 reviewer 闭环。

## 4. 结论

统一工程和接口已达到接收队友实现的条件；正式横向报告因四类实现、全量 EvidenceStore 和冻结评测集缺失而不完整。必须保持阻塞，不用 Smoke 替代正式运行结果。
