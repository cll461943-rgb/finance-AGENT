"""Deterministic contract smoke runner for integration verification."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .contracts import AnswerResponse, Citation, EvidenceRecord, QueryPlan, TraceRecord
from .contracts import TraceStep
from .run_result import BaselineRunResult, RetrievalHit, RunMetadata, RunMetrics

READY_METHOD = "contract-smoke"
MIN_SMOKE_SCORE = 3.0


def load_evidence_store(path: Path) -> list[EvidenceRecord]:
    records = [
        EvidenceRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        raise ValueError(f"EvidenceStore is empty: {path}")
    return records


def load_method_registry(path: Path) -> dict[str, dict]:
    methods = json.loads(path.read_text(encoding="utf-8"))["methods"]
    return {method["method_id"]: method for method in methods}


def _normalize(text: str | None) -> str:
    return re.sub(r"[\W_]+", "", text or "", flags=re.UNICODE).lower()


def _character_similarity(question: str, evidence: EvidenceRecord) -> float:
    query_chars = set(_normalize(question))
    evidence_chars = set(_normalize(f"{evidence.source.title}{evidence.content}"))
    overlap = len(query_chars & evidence_chars) / max(len(query_chars), 1)
    score = overlap
    row_header = _normalize(evidence.table_semantics.row_header)
    column_header = _normalize(evidence.table_semantics.column_header)
    if row_header and row_header in _normalize(question):
        score += 3.0
    if column_header and column_header in _normalize(question):
        score += 2.0
    return score


def _location_label(evidence: EvidenceRecord) -> str:
    location = evidence.location
    if location.sheet_name and location.cell_range:
        return f"Sheet={location.sheet_name}, Cell={location.cell_range}"
    if location.page:
        return f"Page={location.page}"
    return evidence.source.local_path


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def run_contract_smoke(
    query_plan: QueryPlan,
    evidence_store_path: Path,
    *,
    config_path: Path,
    evaluation_set: str = "single_fixture",
    random_seed: int = 42,
) -> BaselineRunResult:
    started_at = datetime.now(UTC)
    started_clock = perf_counter()
    records = load_evidence_store(evidence_store_path)
    scored = sorted(
        (
            (_character_similarity(query_plan.question, evidence), evidence)
            for evidence in records
        ),
        key=lambda item: (-item[0], item[1].evidence_id),
    )
    hits = [
        RetrievalHit(rank=rank, score=round(score, 6), evidence=evidence)
        for rank, (score, evidence) in enumerate(scored[:5], start=1)
    ]
    top = hits[0].evidence
    is_sufficient = (
        hits[0].score >= MIN_SMOKE_SCORE
        and top.quality.validation_status != "rejected"
        and top.table_semantics.value is not None
    )
    quality_warning = top.quality.validation_status != "verified"
    unit = top.table_semantics.unit or "（单位未标注）"
    row_header = (top.table_semantics.row_header or "").replace(" ", "")
    column_header = top.table_semantics.column_header or "目标值"
    trace_id = f"TRACE-{uuid4().hex[:12].upper()}"
    elapsed_ms = (perf_counter() - started_clock) * 1000
    if is_sufficient:
        answer = (
            f"根据{'自动校验样例（尚未人工复核）' if quality_warning else '已核验证据'}，"
            f"《{top.source.title}》中，{row_header}{column_header}为"
            f"{top.table_semantics.value}{unit}。"
        )
        answer_response = AnswerResponse(
            query_id=query_plan.query_id,
            status="answered",
            answer=answer,
            evidence=[top.evidence_id],
            source_title=[top.source.title],
            source_url=[top.source.source_url],
            local_path=[top.source.local_path],
            difficulty="easy",
            qa_type=query_plan.query_type,
            tags=["contract_smoke", f"evidence_{top.quality.validation_status}"],
            citations=[
                Citation(
                    evidence_id=top.evidence_id,
                    location=_location_label(top),
                    quote=top.content,
                )
            ],
            trace_id=trace_id,
            latency_ms=elapsed_ms,
        )
    else:
        answer_response = AnswerResponse(
            query_id=query_plan.query_id,
            status="refused",
            answer=None,
            evidence=[],
            source_title=[],
            source_url=[],
            local_path=[],
            difficulty="unknown",
            qa_type=query_plan.query_type,
            tags=["contract_smoke", "insufficient_evidence"],
            refusal_reason=(
                f"Top evidence score {hits[0].score:.3f} is below the "
                f"{MIN_SMOKE_SCORE:.1f} contract-smoke threshold or evidence is unusable."
            ),
            trace_id=trace_id,
            latency_ms=elapsed_ms,
        )
    ended_at = datetime.now(UTC)
    trace_record = TraceRecord(
        trace_id=trace_id,
        query_id=query_plan.query_id,
        started_at=started_at,
        ended_at=ended_at,
        steps=[
            TraceStep(
                step_no=1,
                module="query_parser",
                input_ref=query_plan.query_id,
                output_ref="QueryPlan",
                status="success",
                elapsed_ms=0,
            ),
            TraceStep(
                step_no=2,
                module="retriever",
                input_ref="QueryPlan",
                output_ref=top.evidence_id,
                status="success",
                message=f"Scored {len(records)} evidence records; returned top 5.",
                elapsed_ms=elapsed_ms,
            ),
            TraceStep(
                step_no=3,
                module="evidence_gate",
                input_ref=top.evidence_id,
                output_ref=top.evidence_id if is_sufficient else None,
                status=(
                    "failed"
                    if not is_sufficient
                    else "warning"
                    if quality_warning
                    else "success"
                ),
                message=(
                    "Evidence is insufficient or unusable; answer generation is closed."
                    if not is_sufficient
                    else "Evidence is auto_checked, not manually verified."
                    if quality_warning
                    else "Evidence is manually verified."
                ),
                elapsed_ms=0,
            ),
            TraceStep(
                step_no=4,
                module="generator",
                input_ref=top.evidence_id,
                output_ref=trace_id if is_sufficient else None,
                status="success" if is_sufficient else "skipped",
                message=(
                    "Deterministic table-value template; no LLM call."
                    if is_sufficient
                    else "Skipped because the evidence gate failed."
                ),
                elapsed_ms=0,
            ),
        ],
        final_status=answer_response.status,
        token_usage=0,
        total_cost=0,
    )
    config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    return BaselineRunResult(
        schema_version="1.0.0",
        metadata=RunMetadata(
            run_id=f"RUN-{uuid4().hex[:12].upper()}",
            method_id=READY_METHOD,
            method_version="0.1.0",
            implementation_status="contract_smoke",
            started_at=started_at,
            ended_at=ended_at,
            config_sha256=config_sha256,
            evidence_store=_portable_path(evidence_store_path),
            evaluation_set=evaluation_set,
            random_seed=random_seed,
        ),
        query_plan=query_plan,
        retrieval_hits=hits,
        answer_response=answer_response,
        trace_record=trace_record,
        metrics=RunMetrics(
            retrieval_hit_count=len(hits),
            top_score=hits[0].score,
            latency_ms=elapsed_ms,
            token_usage=0,
            estimated_cost=0,
        ),
    )
