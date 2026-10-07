import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SAMPLES_DIRECTORY = Path(__file__).resolve().parent
PROJECT_DIRECTORY = SAMPLES_DIRECTORY.parent
if str(PROJECT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIRECTORY))

from document_validation import analyze_document, create_client, prepare_analyzers

DATASETS = {
    "synthetic": SAMPLES_DIRECTORY / "synthetic",
    "official": SAMPLES_DIRECTORY / "official",
}
HANDWRITTEN_SIGNATURE_FIELDS = {
    "handwritten_signature_present",
    "signature_evidence",
    "signature_type",
}


def compare_fields(
    actual_fields: dict[str, Any],
    expected_fields: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    comparisons = {}
    for field_name, expected_value in expected_fields.items():
        actual_value = actual_fields.get(field_name, {}).get("value")
        comparisons[field_name] = {
            "expected": expected_value,
            "actual": actual_value,
            "matches": actual_value == expected_value,
        }
    return comparisons


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    field_totals: dict[str, dict[str, int]] = {}
    passed_cases = 0

    for case in cases:
        comparisons = case["comparisons"]
        if all(comparison["matches"] for comparison in comparisons.values()):
            passed_cases += 1
        for field_name, comparison in comparisons.items():
            totals = field_totals.setdefault(field_name, {"correct": 0, "evaluated": 0})
            totals["evaluated"] += 1
            totals["correct"] += int(comparison["matches"])

    field_metrics = {
        field_name: {
            **totals,
            "accuracy": totals["correct"] / totals["evaluated"],
        }
        for field_name, totals in field_totals.items()
    }
    total_cases = len(cases)
    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "case_accuracy": passed_cases / total_cases if total_cases else 0.0,
        "field_metrics": field_metrics,
    }


def _load_expected(dataset_directory: Path) -> dict[str, dict[str, Any]]:
    expected_path = dataset_directory / "expected_results.json"
    if not expected_path.is_file():
        raise FileNotFoundError(f"Expected results not found: {expected_path}")
    return json.loads(expected_path.read_text(encoding="utf-8"))


def evaluate(dataset_names: list[str], endpoint: str) -> dict[str, Any]:
    client = create_client(endpoint)
    prepare_analyzers(client)
    cases = []

    for dataset_name in dataset_names:
        dataset_directory = DATASETS[dataset_name]
        for filename, expected_fields in _load_expected(dataset_directory).items():
            document_path = dataset_directory / filename
            if not document_path.is_file():
                raise FileNotFoundError(f"Sample document not found: {document_path}")

            include_handwritten_signatures = bool(
                HANDWRITTEN_SIGNATURE_FIELDS.intersection(expected_fields)
            )
            result = analyze_document(
                client,
                document_path,
                include_handwritten_signatures=include_handwritten_signatures,
            )
            comparisons = compare_fields(result["fields"], expected_fields)
            cases.append(
                {
                    "dataset": dataset_name,
                    "file": filename,
                    "passed": all(
                        comparison["matches"]
                        for comparison in comparisons.values()
                    ),
                    "comparisons": comparisons,
                }
            )

    return {"summary": summarize(cases), "cases": cases}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate document validation against labeled sample PDFs."
    )
    parser.add_argument(
        "--dataset",
        choices=["synthetic", "official", "all"],
        default="all",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    endpoint = os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
    if not endpoint:
        parser.error("Set CONTENTUNDERSTANDING_ENDPOINT before running the evaluation.")

    dataset_names = list(DATASETS) if args.dataset == "all" else [args.dataset]
    report = evaluate(dataset_names, endpoint)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(f"Evaluation report written to {args.output.resolve()}")
    else:
        print(serialized)

    if report["summary"]["passed_cases"] != report["summary"]["total_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
