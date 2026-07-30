"""Single command entry point for contract checks and Baseline runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import QueryPlan
from .runner import READY_METHOD, load_evidence_store, load_method_registry
from .runner import run_contract_smoke

REPO = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO / "configs" / "baselines" / "method_registry.json"


def _repository_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regrag")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-methods")

    validate = subparsers.add_parser("validate-evidence")
    validate.add_argument("--evidence-store", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--method", required=True)
    run.add_argument("--query", required=True)
    run.add_argument("--evidence-store", required=True)
    run.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = load_method_registry(DEFAULT_REGISTRY)
    if args.command == "list-methods":
        print(json.dumps(registry, ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate-evidence":
        records = load_evidence_store(_repository_path(args.evidence_store))
        print(json.dumps({"valid_records": len(records)}, ensure_ascii=False))
        return 0

    method = registry.get(args.method)
    if method is None:
        raise SystemExit(f"Unknown method: {args.method}")
    if method["status"] != "contract_smoke":
        raise SystemExit(
            f"Method {args.method} is blocked: {method['blocked_reason']}"
        )
    if args.method != READY_METHOD:
        raise SystemExit(f"No adapter registered for method: {args.method}")

    query_path = _repository_path(args.query)
    evidence_path = _repository_path(args.evidence_store)
    output_path = _repository_path(args.output)
    query_plan = QueryPlan.model_validate_json(query_path.read_text(encoding="utf-8"))
    result = run_contract_smoke(
        query_plan,
        evidence_path,
        config_path=DEFAULT_REGISTRY,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
