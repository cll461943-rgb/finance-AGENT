"""Strict shared contracts for ingestion, retrieval, answering, and tracing."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

QueryType = Literal[
    "regulation_fact",
    "threshold",
    "business_process",
    "table_lookup",
    "cross_file_judgement",
    "out_of_scope",
]
AnswerStatus = Literal["answered", "clarify", "refused", "conflict", "error"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuerySlots(StrictModel):
    agency: str | None = None
    document_title: str | None = None
    clause_no: str | None = None
    metric_name: str | None = None
    period: str | None = None
    institution: str | None = None
    unit: str | None = None
    version_scope: str | None = None


class QueryPlan(StrictModel):
    query_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    query_type: QueryType
    slots: QuerySlots
    need_clarification: bool
    clarification_question: str | None = None
    is_multi_hop: bool
    route_plan: list[
        Literal[
            "bm25",
            "dense",
            "metadata_filter",
            "table_retriever",
            "hierarchical_retrieval",
            "reranker",
            "evidence_gate",
            "python_tool",
        ]
    ] = Field(min_length=1)
    max_hops: int = Field(default=2, ge=1, le=3)


class EvidenceSource(StrictModel):
    title: str = Field(min_length=1)
    local_path: str = Field(min_length=1)
    source_url: str | None
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceLocation(StrictModel):
    page: int | None = Field(default=None, ge=1)
    chapter: str | None
    section: str | None
    clause_no: str | None
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    sheet_name: str | None
    cell_range: str | None


class TableSemantics(StrictModel):
    row_header: str | None
    column_header: str | None
    header_path: list[str]
    value: str | int | float | bool | None
    unit: str | None
    period: str | None
    scale: float | None
    footnote: str | None
    formula: str | None


class RegulationMetadata(StrictModel):
    agency: str | None
    publish_date: str | None
    effective_date: str | None
    expire_date: str | None
    status: Literal["effective", "expired", "repealed", "unknown"] | None
    version_relation: str | None


class EvidenceQuality(StrictModel):
    validation_status: Literal["unreviewed", "auto_checked", "verified", "rejected"]
    support_type: Literal["direct", "supporting", "unknown"]
    sufficiency: Literal["sufficient", "insufficient", "conflicting", "unknown"]
    conflict_group: str | None
    parser_name: str
    parser_version: str
    warnings: list[str]


class EvidenceRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    evidence_id: str = Field(min_length=1)
    doc_id: str = Field(pattern=r"^DOC-[0-9]{3}-[0-9a-f]{12}$")
    evidence_type: Literal[
        "clause", "paragraph", "table_cell", "table_region", "figure_region"
    ]
    source: EvidenceSource
    content: str = Field(min_length=1)
    location: EvidenceLocation
    table_semantics: TableSemantics
    regulation_metadata: RegulationMetadata
    quality: EvidenceQuality


class Citation(StrictModel):
    evidence_id: str
    location: str
    quote: str | None = None


class AnswerResponse(StrictModel):
    query_id: str
    status: AnswerStatus
    answer: str | None
    evidence: list[str]
    source_title: list[str]
    source_url: list[str | None]
    local_path: list[str]
    difficulty: Literal["easy", "medium", "hard", "unknown"]
    qa_type: QueryType
    tags: list[str]
    citations: list[Citation] = Field(default_factory=list)
    clarification_question: str | None = None
    refusal_reason: str | None = None
    trace_id: str
    latency_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def enforce_status_semantics(self) -> "AnswerResponse":
        if self.status == "answered" and (
            not self.answer or not self.evidence or not self.citations
        ):
            raise ValueError("answered responses require answer, evidence, and citations")
        if self.status == "clarify" and not self.clarification_question:
            raise ValueError("clarify responses require clarification_question")
        if self.status == "refused" and not self.refusal_reason:
            raise ValueError("refused responses require refusal_reason")
        return self


class TraceStep(StrictModel):
    step_no: int = Field(ge=1)
    module: Literal[
        "query_parser",
        "retriever",
        "reranker",
        "evidence_gate",
        "tool",
        "generator",
        "validator",
    ]
    input_ref: str | None
    output_ref: str | None
    status: Literal["success", "warning", "failed", "skipped"]
    message: str | None = None
    elapsed_ms: float = Field(ge=0)


class TraceRecord(StrictModel):
    trace_id: str
    query_id: str
    started_at: datetime
    ended_at: datetime | None = None
    steps: list[TraceStep]
    final_status: AnswerStatus
    token_usage: int | None = Field(default=None, ge=0)
    total_cost: float | None = Field(default=None, ge=0)
