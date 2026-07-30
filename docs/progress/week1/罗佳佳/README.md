# 数据底座

本目录完成四项工作：500 份语料清点、五类格式解析 PoC、统一 EvidenceRecord、质量台账。

## 交付物

- `outputs/corpus_manifest.csv`：500 份文件逐项清单及结构探测结果。
- `outputs/poc_samples.csv`：分层 PoC 样本、选择理由、状态、耗时和证据数。
- `outputs/evidence_samples.jsonl`：可追溯证据样例。
- `evidence_schema.json`：EvidenceRecord JSON Schema 2020-12 契约。
- `outputs/parse_quality_log.csv`：PoC 与全语料异常台账。
- `outputs/schema_validation_errors.csv`：Schema 校验结果；只有表头代表零错误。
- `outputs/交付报告.md`：本次运行汇总和验收结论。

## 复现

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r data_governance/requirements.txt
python data_governance/run_data_foundation.py \
  --corpus "03-金融大模型与智能体赛道-南京银行-面向银行业监管制度与统计报表的可信RAG问答/nfra_page_attachments_500"
```

脚本不修改原始语料。重新运行会覆盖 `outputs` 中的同名派生文件。

## 状态解释

- `passed`：完成自动结构检查并生成至少一条可定位证据。
- `warning`：可以解析，但存在来源或版面风险，必须人工复核。
- `failed`：未能生成证据，不能进入索引。
- `validation_status=auto_checked`：仅通过自动校验，不等于人工确认正确。

## 人工抽检动作

在 `parse_quality_log.csv` 中对 `fix_status=review_required` 的行填写：

1. `reviewer` 和 `review_time`；
2. 核对原文件与 EvidenceRecord 的数值、单位、期间、表头路径、页码或单元格；
3. 将确认无误的 `fix_status` 改为 `accepted`；
4. 需要修改解析器的保持 `open`，修复重跑后填写 `fixed_version`。

旧版 `.doc` 当前通过 macOS `textutil` 提取文字，不能保证版面和表格结构完整；这 32 份文件在正式入库前应优先人工复核或转换为 `.docx`。附件的来源标题可以由文件名识别，但多数主文档不在这 500 份附件语料中，因此未伪造 `parent_doc_id`。

