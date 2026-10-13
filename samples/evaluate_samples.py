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

from document_validation import analyze_document, create_client

SYNTHETIC_DIRECTORY = SAMPLES_DIRECTORY / "synthetic"


def compare_result(
    actual: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        name: {
            "expected": expected_value,
            "actual": actual.get(name),
            "matches": actual.get(name) == expected_value,
        }
        for name, expected_value in expected.items()
    }
    return {
        "matches": all(field["matches"] for field in fields.values()),
        "fields": fields,
    }


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total_cases = len(cases)
    passed_cases = sum(
        case["comparison"]["matches"] for case in cases
    )
    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "accuracy": passed_cases / total_cases if total_cases else 0.0,
    }


def evaluate(endpoint: str) -> dict[str, Any]:
    expected_path = SYNTHETIC_DIRECTORY / "expected_results.json"
    expected_results = json.loads(expected_path.read_text(encoding="utf-8"))
    client = create_client(endpoint)
    cases = []

    for filename, expected in expected_results.items():
        document_path = SYNTHETIC_DIRECTORY / filename
        if not document_path.is_file():
            raise FileNotFoundError(f"Sample document not found: {document_path}")

        result = analyze_document(client, document_path)
        comparison = compare_result(result, expected)
        cases.append(
            {
                "file": filename,
                "passed": comparison["matches"],
                "comparison": comparison,
            }
        )

    return {"summary": summarize(cases), "cases": cases}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate document validation on synthetic PDFs."
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        parser.error("Set AZURE_OPENAI_ENDPOINT before running the evaluation.")

    report = evaluate(endpoint)
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
