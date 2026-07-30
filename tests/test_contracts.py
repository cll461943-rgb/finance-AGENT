import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from regrag.contracts import (
    AnswerResponse,
    EvidenceRecord,
    QueryPlan,
    QuerySlots,
    TraceRecord,
)

REPO = Path(__file__).resolve().parents[1]
EVIDENCE_SAMPLE = (
    REPO
    / "docs"
    / "progress"
    / "week1"
    / "罗佳佳"
    / "outputs"
    / "evidence_samples.jsonl"
)


def test_all_week_one_evidence_samples_match_frozen_contract() -> None:
    records = [
        EvidenceRecord.model_validate_json(line)
        for line in EVIDENCE_SAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 128
    assert {record.schema_version for record in records} == {"1.0.0"}


@pytest.mark.parametrize(
    ("schema_file", "model"),
    [
        ("query_plan.schema.json", QueryPlan),
        ("evidence_record.schema.json", EvidenceRecord),
        ("answer_response.schema.json", AnswerResponse),
        ("trace_record.schema.json", TraceRecord),
    ],
)
def test_required_fields_match_published_schema(schema_file: str, model: type) -> None:
    published = json.loads((REPO / "schemas" / schema_file).read_text(encoding="utf-8"))
    generated = model.model_json_schema()
    assert set(generated["required"]) == set(published["required"])


def test_query_plan_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        QueryPlan(
            query_id="Q-1",
            question="测试问题",
            query_type="table_lookup",
            slots=QuerySlots(),
            need_clarification=False,
            is_multi_hop=False,
            route_plan=["table_retriever", "evidence_gate"],
            untracked_option=True,
        )


def test_answered_response_requires_citations() -> None:
    with pytest.raises(ValidationError, match="citations"):
        AnswerResponse(
            query_id="Q-1",
            status="answered",
            answer="42",
            evidence=["E-1"],
            source_title=["source"],
            source_url=[None],
            local_path=["source.xlsx"],
            difficulty="easy",
            qa_type="table_lookup",
            tags=[],
            trace_id="T-1",
        )
