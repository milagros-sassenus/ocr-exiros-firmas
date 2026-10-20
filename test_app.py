import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import _visual_message


class ConfigurationTests(unittest.TestCase):
    def test_missing_deployment_stops_before_upload(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
                "AZURE_OPENAI_DEPLOYMENT": "",
                "APPROVED_REFERENCE_BLOB_CONTAINER_URL": (
                    "https://example.blob.core.windows.net/references"
                ),
            },
            clear=False,
        ):
            app = AppTest.from_file(str(Path(__file__).with_name("app.py"))).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 1)
        self.assertIn("AZURE_OPENAI_DEPLOYMENT", app.error[0].value)
        self.assertEqual(len(app.get("file_uploader")), 0)


class VisualMessageTests(unittest.TestCase):
    def test_suspicious_result_requires_review(self) -> None:
        level, message = _visual_message("suspicious")

        self.assertEqual(level, "error")
        self.assertIn("revision manual", message)

    def test_consistent_result_has_authenticity_disclaimer(self) -> None:
        level, message = _visual_message("consistent")

        self.assertEqual(level, "info")
        self.assertIn("no demuestra autenticidad forense", message)


if __name__ == "__main__":
    unittest.main()
