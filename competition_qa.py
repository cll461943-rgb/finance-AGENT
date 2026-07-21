"""Competition RAG QA runner.

This script is the direct entry point for the NFRA competition dataset:

    python competition_qa.py

It recursively ingests D:\\code\\金融\\dataset, builds or reloads a local vector
index, reads QA数据.xlsx, and writes answers with evidence into reports/.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import numbers
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from llama_index.core import (
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)

from agents.embedding_factory import build_embedding
from agents.llm_factory import build_llm, default_model
from ingestion.ingestor import GwGIngestor

load_dotenv(override=True)

logger = logging.getLogger(__name__)

DEFAULT_DATASET_DIR = Path(r"D:\code\金融\dataset")
DEFAULT_QA_FILE = DEFAULT_DATASET_DIR / "QA数据.xlsx"
DEFAULT_DOCS_DIR = DEFAULT_DATASET_DIR / "数据集" / "nfra_page_attachments_500"
DEFAULT_PERSIST_DIR = Path(".cache/competition_index")
DEFAULT_OUTPUT_DIR = Path("reports/competition_qa")


SYSTEM_PROMPT = """你是金融监管制度与统计报表问答助手。
请只基于给定证据回答问题，不要编造。
要求：
1. 优先给出直接答案，再给必要解释。
2. 涉及数值、日期、机构名称、文件名称、条款时必须保持原文准确。
3. 如果证据不足，明确说明“根据现有资料无法确定”，并列出缺失原因。
4. 输出必须是 JSON，不要使用 Markdown 代码块。
JSON 字段：
{
  "answer": "最终答案",
  "confidence": 0.0到1.0,
  "evidence": [
    {"source": "文件名", "quote": "关键证据摘录", "reason": "为什么支持答案"}
  ]
}
"""


def safe_print(message: Any) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        text = str(message).encode(encoding, errors="replace").decode(encoding)
        print(text)


def has_value(value: Any) -> bool:
    return value is not None and bool(pd.notna(value))


def normalize_text(value: Any) -> str:
    if value is None or not pd.notna(value):
        return ""
    return re.sub(r"\s+", "", str(value))


def extract_quoted_terms(question: str) -> list[str]:
    return [m.group(1) for m in re.finditer("[《“](.*?)[》”]", question or "")]


def find_labeled_file(docs_dir: Path, file_label: Any) -> Path | None:
    if not has_value(file_label):
        return None
    label = str(file_label).strip()
    for path in docs_dir.rglob("*"):
        if path.is_file() and label in path.name:
            return path
    return None


def format_cell_value(value: Any) -> str:
    if value is None or not pd.notna(value):
        return ""
    if isinstance(value, numbers.Real):
        if math.isfinite(value):
            return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value).strip()


def numeric_value(value: Any) -> float | None:
    if value is None or not pd.notna(value):
        return None
    if isinstance(value, numbers.Real):
        return float(value)
    text = str(value).replace(",", "").strip()
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        return float(text)
    return None


def find_row_by_term(df: pd.DataFrame, term: str) -> int | None:
    wanted = normalize_text(term)
    if not wanted:
        return None
    exact_rows = []
    for i in range(df.shape[0]):
        for value in df.iloc[i].tolist():
            if normalize_text(value) == wanted:
                exact_rows.append(i)
                break
    if exact_rows:
        return exact_rows[0]

    candidates: list[tuple[int, int]] = []
    for i in range(df.shape[0]):
        row_text = "".join(normalize_text(v) for v in df.iloc[i].tolist())
        if wanted in row_text:
            candidates.append((len(row_text), i))
    if not candidates:
        return None
    return sorted(candidates)[0][1]


def find_col_by_term(df: pd.DataFrame, term: str) -> int | None:
    wanted = normalize_text(term)
    if not wanted:
        return None
    period_term = re.sub(r"[-/／\\]", "", wanted)
    if period_term in {"季度", "年季度"}:
        return None

    exact_cols = []
    header_limit = min(10, df.shape[0])
    for j in range(df.shape[1]):
        for i in range(header_limit):
            if normalize_text(df.iat[i, j]) == wanted:
                exact_cols.append(j)
                break
    if exact_cols:
        return exact_cols[0]

    parts = [p for p in re.split(r"[/／\\-]", wanted) if p]
    candidates: list[tuple[int, int]] = []
    for j in range(df.shape[1]):
        col_text = "".join(normalize_text(v) for v in df.iloc[:header_limit, j].tolist())
        if wanted in col_text or (parts and all(part in col_text for part in parts)):
            candidates.append((len(col_text), j))
    if not candidates:
        return None
    return sorted(candidates)[0][1]


def quarter_index(question: str) -> int:
    q = question or ""
    mapping = [("四季度", 4), ("三季度", 3), ("二季度", 2), ("一季度", 1)]
    for marker, idx in mapping:
        if marker in q:
            return idx
    return 1


def first_numeric_after_label(df: pd.DataFrame, row_idx: int, question: str) -> Any:
    row = df.iloc[row_idx].tolist()
    numeric_positions = []
    for j, value in enumerate(row):
        if isinstance(value, (int, float)) and pd.notna(value):
            numeric_positions.append((j, value))
            continue
        text = str(value).replace(",", "")
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
            numeric_positions.append((j, float(text)))
    if not numeric_positions:
        return None
    idx = min(quarter_index(question), len(numeric_positions)) - 1
    return numeric_positions[idx][1]


def try_answer_excel_question(
    docs_dir: Path, question: str, question_meta: dict[str, Any]
) -> dict[str, Any] | None:
    if str(question_meta.get("source_type", "")).lower() != "excel":
        return None
    target = find_labeled_file(docs_dir, question_meta.get("file_label"))
    if not target:
        return None

    terms = extract_quoted_terms(question)
    if len(terms) < 2:
        return None
    row_term = terms[-2]
    col_term = terms[-1]

    try:
        sheets = pd.read_excel(target, sheet_name=None, header=None)
    except Exception as exc:
        logger.warning("Structured Excel read failed for %s: %s", target.name, exc)
        return None

    for sheet_name, df in sheets.items():
        row_idx = find_row_by_term(df, row_term)
        if row_idx is None:
            continue

        value = None
        col_idx = find_col_by_term(df, col_term)
        if col_idx is not None:
            value = df.iat[row_idx, col_idx]
        if numeric_value(value) is None:
            value = first_numeric_after_label(df, row_idx, question)

        answer = format_cell_value(value)
        if not answer:
            continue
        return {
            "answer": answer,
            "confidence": 1.0,
            "evidence": [
                {
                    "source": target.name,
                    "quote": f"{sheet_name} | {row_term} | {col_term} -> {answer}",
                    "reason": "structured_excel_cell_lookup",
                }
            ],
            "retrieved_evidence": [
                {
                    "rank": 1,
                    "source": target.name,
                    "file_path": str(target),
                    "score": 1.0,
                    "text": f"Structured Excel lookup: {row_term} / {col_term}",
                }
            ],
        }
    return None


def build_or_load_index(
    docs_dir: Path,
    persist_dir: Path,
    *,
    rebuild: bool = False,
    embedding_provider: str = "hash",
):
    embed_model = build_embedding(provider=embedding_provider)
    Settings.embed_model = embed_model

    if persist_dir.exists() and not rebuild:
        storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
        return load_index_from_storage(storage_context, embed_model=embed_model)

    ingestor = GwGIngestor()
    documents = ingestor.ingest_directory(str(docs_dir))
    if not documents:
        raise ValueError(f"No documents found in {docs_dir}")

    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    persist_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(persist_dir))
    return index


def load_questions(qa_file: Path, *, limit: int | None = None) -> pd.DataFrame:
    df = pd.read_excel(qa_file)
    question_col = detect_question_column(df)
    if question_col != "question":
        df = df.rename(columns={question_col: "question"})
    df["question"] = df["question"].astype(str).str.strip()
    df = df[df["question"].ne("")]
    if limit:
        df = df.head(limit)
    return df.reset_index(drop=True)


def detect_question_column(df: pd.DataFrame) -> str:
    preferred = ["question", "问题", "题目", "query", "Question", "问题描述"]
    for col in preferred:
        if col in df.columns:
            return col

    best_col = None
    best_score = -1
    for col in df.columns:
        series = df[col].dropna().astype(str)
        score = series.str.contains(r"[？?]", regex=True).sum()
        score += series.str.len().mean() if len(series) else 0
        if score > best_score:
            best_score = score
            best_col = col
    if best_col is None:
        raise ValueError("QA file has no usable question column")
    return str(best_col)


def answer_question(
    llm,
    retriever,
    question: str,
    question_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_meta = question_meta or {}
    nodes = retriever.retrieve(question)
    evidence_blocks = []
    evidence_rows = []
    for idx, node_with_score in enumerate(nodes, 1):
        node = node_with_score.node
        meta = node.metadata or {}
        text = node.get_content().strip()
        source = meta.get("source") or meta.get("file_path") or f"chunk-{idx}"
        evidence_blocks.append(
            f"[{idx}] source={source}\n"
            f"path={meta.get('file_path', '')}\n"
            f"score={node_with_score.score}\n"
            f"{text[:2500]}"
        )
        evidence_rows.append(
            {
                "rank": idx,
                "source": source,
                "file_path": meta.get("file_path", ""),
                "score": node_with_score.score,
                "text": text[:1000],
            }
        )

    option_lines = []
    for key in ["option_a", "option_b", "option_c", "option_d"]:
        value = question_meta.get(key)
        if has_value(value):
            option_lines.append(f"{key[-1].upper()}: {value}")
    meta_lines = []
    for key in ["source_type", "qa_type", "source_title", "file_label"]:
        value = question_meta.get(key)
        if has_value(value):
            meta_lines.append(f"{key}: {value}")

    user_prompt = f"问题：{question}\n\n"
    if option_lines:
        user_prompt += (
            "候选选项：\n"
            + "\n".join(option_lines)
            + "\n请先在证据中定位题目指定的行、列、期间或指标，再返回对应选项的数值文本；不要只因为某个选项出现在同一文件中就选择它。\n\n"
        )
    if meta_lines:
        user_prompt += "问题元数据（不含标准答案）：\n" + "\n".join(meta_lines) + "\n\n"
    user_prompt += "证据：\n" + "\n\n".join(evidence_blocks) + "\n\n请按系统要求输出 JSON。"
    response = llm.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    raw = getattr(response, "content", str(response))
    parsed = parse_json_object(raw)
    parsed.setdefault("answer", raw)
    parsed.setdefault("confidence", 0.0)
    parsed.setdefault("evidence", [])
    parsed["retrieved_evidence"] = evidence_rows
    return parsed


def parse_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"answer": raw}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else {"answer": raw}
            except json.JSONDecodeError:
                pass
    return {"answer": raw, "confidence": 0.0, "evidence": []}


def write_outputs(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = output_dir / f"answers_{stamp}.jsonl"
    xlsx_path = output_dir / f"answers_{stamp}.xlsx"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    flat_rows = []
    for row in rows:
        flat = {
            **{
                k: v
                for k, v in row.items()
                if k not in {"generated_evidence", "retrieved_evidence"}
            },
            "generated_evidence": json.dumps(
                row.get("generated_evidence", []), ensure_ascii=False
            ),
            "retrieved_evidence": json.dumps(
                row.get("retrieved_evidence", []), ensure_ascii=False
            ),
        }
        flat_rows.append(flat)
    pd.DataFrame(flat_rows).to_excel(xlsx_path, index=False)
    return {"jsonl": str(jsonl_path), "xlsx": str(xlsx_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NFRA competition RAG QA.")
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR))
    parser.add_argument("--qa-file", default=str(DEFAULT_QA_FILE))
    parser.add_argument("--persist-dir", default=str(DEFAULT_PERSIST_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--model", default=default_model("dashscope"))
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    )

    index = build_or_load_index(
        Path(args.docs_dir),
        Path(args.persist_dir),
        rebuild=args.rebuild_index,
    )
    retriever = index.as_retriever(similarity_top_k=args.top_k)
    llm = build_llm(provider="dashscope", model=args.model, temperature=0.0)
    questions = load_questions(Path(args.qa_file), limit=args.limit)

    rows: list[dict[str, Any]] = []
    for i, original_row in questions.iterrows():
        question = original_row["question"]
        safe_print(f"[{i + 1}/{len(questions)}] {question}")
        question_meta = {
            key: original_row.get(key)
            for key in [
                "source_type",
                "qa_type",
                "source_title",
                "file_label",
                "option_a",
                "option_b",
                "option_c",
                "option_d",
            ]
        }
        result = try_answer_excel_question(Path(args.docs_dir), question, question_meta)
        if result is None:
            result = answer_question(llm, retriever, question, question_meta=question_meta)
        rows.append(
            {
                **original_row.to_dict(),
                "generated_answer": result.get("answer", ""),
                "generated_confidence": result.get("confidence", 0.0),
                "generated_evidence": result.get("evidence", []),
                "retrieved_evidence": result.get("retrieved_evidence", []),
            }
        )

    paths = write_outputs(rows, Path(args.output_dir))
    safe_print(json.dumps(paths, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
