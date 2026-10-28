import unittest
from datetime import date, timedelta
from validator import validate_document


class ValidatorTests(unittest.TestCase):
    def test_missing_reference_is_flagged(self):
        result = validate_document({
            "filename": "sample.pdf", "document_type": "NOC", "reference_number": "",
            "issue_date": "", "expiry_date": ""
        }, "Demo College")
        self.assertIn("MISSING_REFERENCE", [finding["code"] for finding in result["findings"]])

    def test_synthetic_record_can_match(self):
        result = validate_document({
            "filename": "sample.pdf", "document_type": "Accreditation Certificate",
            "reference_number": "CERT12345", "issue_date": "2024-01-10", "expiry_date": "2026-01-09"
        }, "ABC Engineering College")
        self.assertEqual(result["verification_status"], "Matched synthetic test record")
        self.assertIn("EXPIRED", [finding["code"] for finding in result["findings"]])

    def test_mismatch_is_flagged(self):
        result = validate_document({
            "filename": "sample.pdf", "document_type": "NOC", "reference_number": "CERT12345",
            "issue_date": "2024-01-10", "expiry_date": "2026-01-09"
        }, "Different College")
        self.assertEqual(result["verification_status"], "Mismatch detected")
        self.assertIn("SOURCE_MISMATCH", [finding["code"] for finding in result["findings"]])

    def test_invalid_date_is_flagged(self):
        result = validate_document({
            "filename": "sample.pdf", "document_type": "NOC", "reference_number": "UNKNOWN",
            "issue_date": "2026-99-99", "expiry_date": "not-a-date"
        }, "Demo College")
        codes = [finding["code"] for finding in result["findings"]]
        self.assertIn("INVALID_ISSUE_DATE", codes)
        self.assertIn("INVALID_EXPIRY_DATE", codes)


if __name__ == "__main__":
    unittest.main()
