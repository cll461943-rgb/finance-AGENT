# 可信 RegRAG

面向银行业监管制度与统计报表的可信 RAG 问答项目，参加第五届中国研究生金融科技创新大赛。

项目目标是围绕监管制度查询、统计报表取数和跨文件合规判断，建立可追溯、可校验、可复现的问答链路。当前仓库按“进度材料 → 统一契约 → Baseline → 评测 → 交付结果”组织。

## 当前状态

- 第一周：业务场景、用户故事、评测初稿、500 份语料清点、16 份解析 PoC、接口设计稿已归档。
- 第二周：统一仓库、四类核心接口、公平比较协议、方法注册表和契约 Smoke 入口已完成。
- 契约验证：128 条第一周 EvidenceRecord 样例全部通过严格模型校验，自动化测试为 `13 passed`。
- 已知边界：`auto_checked` 仅表示自动结构校验，不等于人工确认；Hybrid、FinSage、RegulatoryRAG-ML、HiREC-Lite 尚无可接入实现和正式横向指标。

## 目录

```text
docs/
└── progress/
    ├── project/       # 项目计划书
    ├── week1/         # 第一周任务与成员交付
    └── week2/         # 第二周任务与后续交付
```

```text
configs/      # 可复现实验配置
data/         # 数据说明与版本引用，不提交受限原始语料
index/        # 索引构建说明
baselines/    # 统一 Baseline 接口
evaluation/   # 评测协议与脚本
outputs/      # 可公开的运行结果
schemas/      # QueryPlan / EvidenceRecord / AnswerResponse / TraceRecord
src/          # RegRAG 主工程
tests/        # 契约与最小联调测试
```

## 快速验证

```powershell
$env:PYTHONPATH = "src"
py -3.12 -m pytest -q
py -3.12 -m regrag list-methods
py -3.12 -m regrag validate-evidence `
  --evidence-store "docs/progress/week1/罗佳佳/outputs/evidence_samples.jsonl"
py -3.12 -m regrag run `
  --method contract-smoke `
  --query examples/query_table_lookup.json `
  --evidence-store "docs/progress/week1/罗佳佳/outputs/evidence_samples.jsonl" `
  --output outputs/smoke/contract_smoke_result.json
```

`contract-smoke` 只验证统一入口、契约、引用和 Trace，不是 Hybrid 或完整 RegRAG 的正式性能实现。

## 数据与合规

- 不提交 500 份赛题原始附件、报名材料、承诺书、密钥或模型缓存。
- 外部开源项目只作为参考或依赖，必须记录来源、许可证和实际改动。
- 所有运行结果必须绑定数据版本、解析器版本、模型、参数和时间戳。

## 负责人

陈伦禄（项目协调、架构整合、代码审查与周验收）
