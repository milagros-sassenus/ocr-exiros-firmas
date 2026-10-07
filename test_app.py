import unittest

from app import _result_messages


class ResultMessageTests(unittest.TestCase):
    def test_reports_each_missing_signal(self) -> None:
        self.assertEqual(
            _result_messages(
                "compliance_letter",
                "none",
                False,
                "consistent",
            ),
            [
                ("warning", "No se detecto firma manuscrita ni electronica."),
                (
                    "warning",
                    "No se detecto membrete de la compania o institucion.",
                ),
            ],
        )

    def test_does_not_show_success_when_letterhead_is_missing(self) -> None:
        messages = _result_messages(
            "compliance_letter",
            "handwritten",
            False,
            "consistent",
        )

        self.assertEqual(
            messages,
            [
                (
                    "warning",
                    "No se detecto membrete de la compania o institucion.",
                )
            ],
        )

    def test_shows_authenticity_disclaimer_when_all_signals_are_present(self) -> None:
        self.assertEqual(
            _result_messages(
                "bank_certificate",
                "handwritten",
                True,
                "consistent",
            ),
            [
                (
                    "info",
                    "Se detectaron firma y membrete, y la apariencia coincide con el "
                    "tipo de documento. Esto no confirma que sea autentico.",
                )
            ],
        )

    def test_reports_suspicious_appearance_as_error(self) -> None:
        messages = _result_messages(
            "bank_certificate",
            "handwritten",
            True,
            "suspicious",
        )

        self.assertEqual(messages[0][0], "error")

if __name__ == "__main__":
    unittest.main()
