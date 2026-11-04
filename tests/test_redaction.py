
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction import redact_message


class TestRedaction(unittest.TestCase):

    def test_email_redaction(self):
        text = "My email is alex@example.com."

        result = redact_message(text)

        self.assertNotIn("alex@example.com", result)
        self.assertIn("[REDACTED]", result)

    def test_multiple_emails(self):
        text = "Contact alex@example.com or sam@example.org."

        result = redact_message(text)

        self.assertNotIn("alex@example.com", result)
        self.assertNotIn("sam@example.org", result)
        self.assertEqual(result.count("[REDACTED]"), 2)

    def test_safe_message(self):
        text = "How can I change my PIN?"

        result = redact_message(text)

        self.assertEqual(result, text)

    def test_explicit_pin(self):
        text = "My PIN is 4826."

        result = redact_message(text)

        self.assertNotIn("4826", result)
        self.assertIn("[REDACTED]", result)


if __name__ == "__main__":
    unittest.main()
