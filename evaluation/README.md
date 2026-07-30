# Evaluation

主公平结论按 `docs/contracts/Baseline公平比较协议_V1.0.md` 执行。

- 端到端：CoreEval-80。
- 检索：RetrievalGold-40。
- 拒答/澄清：单独子集，不把澄清和拒答合并计分。
- 必报：Recall@5/10、nDCG@10、Citation Hit、答案准确率、P50/P95、Token 和估算成本。

论文原生设置只能作为补充实验，不得混入主公平结论。
