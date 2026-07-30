# Outputs

只提交可公开、可复现且不含敏感信息的结果。

- `smoke/contract_smoke_result.json`：契约 Smoke 的统一结果样例。
- 正式结果命名：`YYYYMMDDTHHMMSSZ__方法__数据版本__配置哈希前8位.json`。
- 每个正式结果必须包含方法版本、配置哈希、EvidenceStore 路径或版本、评测集、随机种子、Trace、延迟、Token 和成本。

缓存、索引、完整模型输出和受限数据衍生物默认忽略。
