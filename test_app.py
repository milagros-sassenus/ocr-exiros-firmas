import unittest

from app import _visual_message


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
