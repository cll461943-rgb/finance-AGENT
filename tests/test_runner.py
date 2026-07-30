import json
from pathlib import Path

import pytest

from regrag.cli import main
from regrag.contracts import QueryPlan
from regrag.runner import load_method_registry, run_contract_smoke

REPO = Path(__file__).resolve().parents[1]
QUERY = REPO / "examples" / "query_table_lookup.json"
EVIDENCE = (
    REPO
    / "docs"
    / "progress"
    / "week1"
    / "罗佳佳"
    / "outputs"
    / "evidence_samples.jsonl"
)
REGISTRY = REPO / "configs" / "baselines" / "method_registry.json"


def test_contract_smoke_returns_traceable_table_answer() -> None:
    query = QueryPlan.model_validate_json(QUERY.read_text(encoding="utf-8"))
    result = run_contract_smoke(query, EVIDENCE, config_path=REGISTRY)
    assert result.answer_response.status == "answered"
    assert result.answer_response.evidence == ["DOC-032-2ddfb401b298-CELL-001"]
    assert "52145.77亿元" in result.answer_response.answer
    assert "尚未人工复核" in result.answer_response.answer
    assert result.trace_record.token_usage == 0
    assert result.metrics.retrieval_hit_count == 5


def test_registry_marks_unimplemented_methods_blocked() -> None:
    registry = load_method_registry(REGISTRY)
    assert registry["contract-smoke"]["status"] == "contract_smoke"
    assert registry["hybrid"]["status"] == "blocked"
    assert registry["hirec-lite"]["adapter"] is None


def test_cli_writes_uniform_result(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    exit_code = main(
        [
            "run",
            "--method",
            "contract-smoke",
            "--query",
            str(QUERY),
            "--evidence-store",
            str(EVIDENCE),
            "--output",
            str(output),
        ]
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["schema_version"] == "1.0.0"
    assert payload["metadata"]["method_id"] == "contract-smoke"


def test_cli_refuses_blocked_method(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="blocked"):
        main(
            [
                "run",
                "--method",
                "hybrid",
                "--query",
                str(QUERY),
                "--evidence-store",
                str(EVIDENCE),
                "--output",
                str(tmp_path / "result.json"),
            ]
        )
