# Baselines

统一方法注册表位于 `configs/baselines/method_registry.json`，运行入口为 `python -m regrag`。

| 方法 | 当前状态 | 说明 |
|---|---|---|
| `contract-smoke` | 可运行 | 只验证契约、EvidenceStore、引用与 Trace |
| `hybrid` | 阻塞 | 缺 BM25 + Dense + RRF + Reranker 实现和 20 题日志 |
| `finsage-adapted` | 阻塞 | 缺去除场景硬编码后的多路径检索实现 |
| `regulatory-rag-ml-adapted` | 阻塞 | 缺监管特征、Score Filter、引用与拒答分支 |
| `hirec-lite` | 阻塞 | 缺文档级到证据级检索、完整性判断和单次补查 |

任何方法接入前必须返回统一 `BaselineRunResult`，并通过 `tests/` 中的契约检查。
