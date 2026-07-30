# Data

本目录只保存数据版本说明和公开样例引用。

- 受限原始语料不进入 Git。
- 当前契约 Smoke 使用 `docs/progress/week1/罗佳佳/outputs/evidence_samples.jsonl`，共 128 条、来自 16 份 PoC 文件。
- 正式 EvidenceStore 必须另行生成，并记录 `corpus_manifest`、解析器版本、SHA-256、失败清单和人工复核状态。
- `auto_checked` 不能改写为 `verified`；缺少 `parent_doc_id`、版本状态或单位时不得臆造。
