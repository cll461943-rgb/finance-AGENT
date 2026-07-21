# FinRegAgents Competition Edition

这个工作副本已改成赛题数据集适配版。

## 模型

只使用一种 LLM：

- Provider: `dashscope`
- Model: `deepseek-v4-pro`
- API Key: `DASHSCOPE_API_KEY`
- Endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1`

`DASHSCOPE_BASE_URL` 可选，用于覆盖默认百炼兼容接口地址。

## 数据

默认赛题数据目录：

```powershell
D:\code\金融\dataset
```

批量 QA 默认索引附件目录：

```powershell
D:\code\金融\dataset\数据集\nfra_page_attachments_500
```

ingestion 会递归扫描文档目录，自动跳过 `__MACOSX`、`._*` 和 `QA数据.xlsx`，并读取：

- PDF
- Word: `.docx`，旧 `.doc` 会尽量抽取文本
- Excel/CSV: `.xlsx`、`.xls`、`.csv`
- JSON/YAML/TXT/LOG
- 图片占位元数据

## 运行

批量回答 `QA数据.xlsx`：

```powershell
pip install -r requirements.txt
python competition_qa.py
```

首次运行会建立 `.cache/competition_index`，之后会复用索引。强制重建：

```powershell
python competition_qa.py --rebuild-index
```

快速试跑前 3 题：

```powershell
python competition_qa.py --limit 3 --verbose
```

保留原审计 pipeline 入口：

```powershell
pip install -r requirements.txt
python pipeline.py --regulatorik gwg --institution "Competition"
```

显式指定输入目录：

```powershell
python pipeline.py --input D:\code\金融\dataset --regulatorik gwg
```

启动 UI：

```powershell
streamlit run app.py
```

## 说明

向量检索默认使用本地 Hash Embedding，因此项目只需要 `DASHSCOPE_API_KEY` 一个云端凭证。原论文自带 demo 数据不再作为默认输入。
