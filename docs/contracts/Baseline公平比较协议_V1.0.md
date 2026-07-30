# Baseline 公平比较协议 V1.0

负责人：陈伦禄。适用方法：Hybrid、FinSage-Adapted、RegulatoryRAG-ML-Adapted、HiREC-Lite，以及第三周完整 RegRAG。

## 1. 主结论控制变量

| 控制项 | 统一要求 |
|---|---|
| 原始语料 | 同一 `corpus_manifest`、相同排除与警告清单 |
| EvidenceStore | 同一文件与 SHA-256；同一解析器版本 |
| 索引 | 同一 BM25、BGE-M3 Dense、Metadata 索引版本 |
| 模型 | 固定 Embedding、通用 Reranker 和生成 LLM |
| 候选预算 | 初召回 Top-20、重排 Top-10；总候选预算一致 |
| Agent 预算 | HiREC/RegRAG 最多一次补查；额外调用次数单列 |
| Prompt | 相同回答格式、引用、拒答和资料库外约束 |
| 评测集 | CoreEval-80、RetrievalGold-40、同一划分和随机种子 42 |
| 输出 | 统一 BaselineRunResult、AnswerResponse 和 TraceRecord |

方法专有能力可以改变检索路径和排序逻辑，但不得暗中扩大候选、LLM 调用或语料范围。

## 2. 指标

- 检索：Recall@5、Recall@10、nDCG@10、Evidence Hit。
- 回答：答案准确率、Citation Hit、关键数字/日期/机构/文号错误率。
- 可信：拒答正确率、澄清正确率、冲突识别率；三者分开统计。
- 效率：P50、P95、端到端耗时、检索耗时、LLM 调用数、Token 和估算成本。
- 稳定：失败率、重试数和不可复现用例数。

## 3. 方法边界

- Hybrid：BM25 + Dense + RRF + 通用 Reranker，作为统一下界。
- FinSage-Adapted：允许标题/摘要、Metadata、Bundle Expansion；必须移除原场景硬编码并声明 HyDE 开关。
- RegulatoryRAG-ML-Adapted：允许监管特征和轻量 LTR/规则；qrels 不足时不得宣称复现论文最优 LTR。
- HiREC-Lite：文档级到证据级检索，最多一次补充查询，不得无限多跳。
- 完整 RegRAG：第三周起加入动态路由、跨文件多跳、Evidence Gate、工具和自核。

## 4. 运行与审计

每次运行保存配置哈希、Git commit、EvidenceStore 哈希、评测集版本、方法版本、模型、随机种子、时间戳和环境说明。失败与空结果必须进入结果表，不能从分母删除。

主结论只使用本协议的受控运行。论文原生设置或额外预算实验单独报告，不能与主表混合。

## 5. 通过门槛

方法只有在契约测试通过、全量运行可复现、结果字段完整、无资料库外补答且无 Critical 审查问题时，才能标记 `benchmark_ready`。当前只有 `contract-smoke` 可运行，且它不属于正式方法。
