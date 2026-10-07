import unittest
from unittest.mock import patch

from azure.ai.contentunderstanding.models import BooleanField, StringField

from document_validation import (
    _field_to_dict,
    _knowledge_sources,
    _review_required,
    _signature_type,
)
from samples.evaluate_samples import compare_fields, summarize


class FieldFormattingTests(unittest.TestCase):
    def test_includes_available_evidence(self) -> None:
        field = StringField(
            type="string",
            field_type="string",
            value_string="visible signature on page 1",
            confidence=0.91,
            source="D(1,0.1,0.2,0.3,0.4)",
        )

        self.assertEqual(
            _field_to_dict(field),
            {
                "value": "visible signature on page 1",
                "confidence": 0.91,
                "source": "D(1,0.1,0.2,0.3,0.4)",
            },
        )

    def test_omits_unavailable_optional_evidence(self) -> None:
        field = BooleanField(
            type="boolean",
            field_type="boolean",
            value_boolean=True,
        )

        self.assertEqual(_field_to_dict(field), {"value": True})


class SignatureTypeTests(unittest.TestCase):
    def test_combines_known_signature_signals(self) -> None:
        self.assertEqual(_signature_type(True, True), "both")
        self.assertEqual(_signature_type(True, False), "handwritten")
        self.assertEqual(_signature_type(False, True), "electronic")
        self.assertEqual(_signature_type(False, False), "none")

    def test_preserves_unknown_electronic_signature_signal(self) -> None:
        self.assertEqual(_signature_type(False, None), "inconclusive")


class ReviewDecisionTests(unittest.TestCase):
    def test_requires_review_when_a_required_signal_is_missing(self) -> None:
        fields = {
            "document_type": {"value": "compliance_letter"},
            "signature_type": {"value": "handwritten"},
            "letterhead_present": {"value": False},
            "visual_consistency": {"value": "consistent"},
        }

        self.assertTrue(_review_required(fields))

    def test_does_not_require_review_when_visual_signals_pass(self) -> None:
        fields = {
            "document_type": {"value": "bank_certificate"},
            "signature_type": {"value": "handwritten"},
            "letterhead_present": {"value": True},
            "visual_consistency": {"value": "consistent"},
        }

        self.assertFalse(_review_required(fields))


class KnowledgeSourceTests(unittest.TestCase):
    def test_builds_labeled_source_from_environment(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "CONTENTUNDERSTANDING_TRAINING_DATA_SAS_URL": (
                    "https://example.blob.core.windows.net/official?sig=test"
                ),
                "CONTENTUNDERSTANDING_TRAINING_DATA_PREFIX": "golden",
            },
            clear=True,
        ):
            source = _knowledge_sources()[0].as_dict()

        self.assertEqual(source["kind"], "labeledData")
        self.assertEqual(source["prefix"], "golden")
        self.assertEqual(source["fileListPath"], "")

    def test_requires_training_data_to_create_analyzer(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                "CONTENTUNDERSTANDING_TRAINING_DATA_SAS_URL",
            ):
                _knowledge_sources()


class SampleEvaluationTests(unittest.TestCase):
    def test_compares_only_labeled_fields(self) -> None:
        comparisons = compare_fields(
            {
                "handwritten_signature_present": {"value": False},
                "letterhead_present": {"value": True},
                "unlabeled_field": {"value": "ignored"},
            },
            {
                "handwritten_signature_present": False,
                "letterhead_present": True,
            },
        )

        self.assertEqual(
            comparisons,
            {
                "handwritten_signature_present": {
                    "expected": False,
                    "actual": False,
                    "matches": True,
                },
                "letterhead_present": {
                    "expected": True,
                    "actual": True,
                    "matches": True,
                },
            },
        )

    def test_summarizes_case_and_field_accuracy(self) -> None:
        summary = summarize(
            [
                {
                    "comparisons": {
                        "signature": {"matches": True},
                        "letterhead": {"matches": True},
                    }
                },
                {
                    "comparisons": {
                        "signature": {"matches": False},
                        "letterhead": {"matches": True},
                    }
                },
            ]
        )

        self.assertEqual(summary["passed_cases"], 1)
        self.assertEqual(summary["case_accuracy"], 0.5)
        self.assertEqual(
            summary["field_metrics"]["signature"],
            {"correct": 1, "evaluated": 2, "accuracy": 0.5},
        )
        self.assertEqual(
            summary["field_metrics"]["letterhead"],
            {"correct": 2, "evaluated": 2, "accuracy": 1.0},
        )


if __name__ == "__main__":
    unittest.main()
