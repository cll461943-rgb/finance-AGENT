# Index

索引产物不提交仓库，只提交构建脚本、配置和可复现元数据。

正式 Baseline 应共享同一版本的：

- BM25 索引；
- BGE-M3 Dense 索引；
- Metadata 索引；
- EvidenceStore 排除/警告清单。

每次构建至少记录语料哈希、EvidenceStore 哈希、模型名与版本、条目数、耗时和构建时间。
