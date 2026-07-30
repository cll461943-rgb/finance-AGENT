"""Uniform result envelope shared by every Baseline adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .contracts import (
    AnswerResponse,
    EvidenceRecord,
    QueryPlan,
    StrictModel,
    TraceRecord,
)


class RetrievalHit(StrictModel):
    rank: int = Field(ge=1)
    score: float
    evidence: EvidenceRecord


class RunMetadata(StrictModel):
    run_id: str
    method_id: str
    method_version: str
    implementation_status: Literal["contract_smoke", "benchmark_ready"]
    started_at: datetime
    ended_at: datetime
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_store: str
    evaluation_set: str
    random_seed: int


class RunMetrics(StrictModel):
    retrieval_hit_count: int = Field(ge=0)
    top_score: float | None
    latency_ms: float = Field(ge=0)
    token_usage: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)


class BaselineRunResult(StrictModel):
    schema_version: Literal["1.0.0"]
    metadata: RunMetadata
    query_plan: QueryPlan
    retrieval_hits: list[RetrievalHit]
    answer_response: AnswerResponse
    trace_record: TraceRecord
    metrics: RunMetrics
