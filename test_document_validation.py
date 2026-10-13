import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from document_validation import (
    DocumentAssessment,
    _build_input,
    _openai_base_url,
    analyze_document,
)
from samples.evaluate_samples import compare_result, summarize


class EndpointTests(unittest.TestCase):
    def test_adds_openai_v1_path(self) -> None:
        self.assertEqual(
            _openai_base_url("https://example.openai.azure.com"),
            "https://example.openai.azure.com/openai/v1/",
        )

    def test_preserves_complete_openai_v1_path(self) -> None:
        self.assertEqual(
            _openai_base_url("https://example.openai.azure.com/openai/v1/"),
            "https://example.openai.azure.com/openai/v1/",
        )


class InputTests(unittest.TestCase):
    def test_distinguishes_user_approved_references_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            document_path = Path(temporary_directory) / "target.pdf"
            document_path.write_bytes(b"target")
            request_input = _build_input(
                document_path,
                references=[("approved.pdf", b"reference")],
                page_images=[b"image"],
            )

        content = request_input[0]["content"]
        self.assertIn("user-approved real", content[0]["text"])
        self.assertIn("USER-APPROVED POSITIVE REFERENCE", content[1]["text"])
        self.assertEqual(content[2]["filename"], "approved.pdf")
        self.assertIn("TARGET DOCUMENT: target.pdf", content[3]["text"])
        self.assertEqual(content[4]["filename"], "target.pdf")
        self.assertEqual(content[6]["type"], "input_image")
        self.assertEqual(content[6]["detail"], "high")

    def test_rejects_combined_input_over_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            document_path = Path(temporary_directory) / "target.pdf"
            document_path.write_bytes(b"target")
            with patch("document_validation.MAX_INPUT_BYTES", 10):
                with self.assertRaisesRegex(ValueError, "total less than 50 MB"):
                    _build_input(
                        document_path,
                        references=[("approved.pdf", b"reference")],
                        page_images=[b"image"],
                    )


class AnalyzeDocumentTests(unittest.TestCase):
    def test_returns_required_assessment(self) -> None:
        assessment = DocumentAssessment(
            signature_present=True,
            letterhead_present=True,
            document_type="bank certificate",
            visual_authenticity="consistent",
            visual_findings="Expected branding and structure are present.",
        )
        client = Mock()
        client.responses.parse.return_value = SimpleNamespace(
            output_parsed=assessment
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            document_path = Path(temporary_directory) / "target.pdf"
            document_path.write_bytes(b"target")
            with patch.dict(
                "os.environ",
                {"AZURE_OPENAI_DEPLOYMENT": "test-model"},
                clear=False,
            ), patch(
                "document_validation._render_pdf_pages",
                return_value=[b"image"],
            ):
                result = analyze_document(
                    client,
                    document_path,
                    references=[("approved.pdf", b"reference")],
                )

        self.assertTrue(result["signature_present"])
        self.assertTrue(result["letterhead_present"])
        self.assertEqual(result["visual_authenticity"], "consistent")
        self.assertEqual(result["reference_files"], ["approved.pdf"])
        client.responses.parse.assert_called_once()


class SampleEvaluationTests(unittest.TestCase):
    def test_compares_all_labeled_fields(self) -> None:
        comparison = compare_result(
            {
                "signature_present": True,
                "letterhead_present": True,
                "visual_authenticity": "suspicious",
            },
            {
                "signature_present": True,
                "letterhead_present": True,
                "visual_authenticity": "suspicious",
            },
        )

        self.assertTrue(comparison["matches"])
        self.assertEqual(comparison["fields"]["letterhead_present"]["actual"], True)

    def test_summarizes_accuracy(self) -> None:
        summary = summarize(
            [
                {"comparison": {"matches": True}},
                {"comparison": {"matches": False}},
            ]
        )

        self.assertEqual(
            summary,
            {
                "total_cases": 2,
                "passed_cases": 1,
                "accuracy": 0.5,
            },
        )


if __name__ == "__main__":
    unittest.main()
