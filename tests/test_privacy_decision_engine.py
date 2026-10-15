
import sys
import unittest
from pathlib import Path

# Allow imports from the src directory.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from privacy_decision_engine import (
    train_model,
    analyze_message,
)


class TestPrivacyDecisionEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Train once for the entire test class.
        cls.model = train_model()

    def test_safe_pin_question(self):
        result = analyze_message(
            "How can I change my PIN?",
            self.model
        )

        self.assertEqual(
            result["decision"],
            "SAFE"
        )

    def test_explicit_pin(self):
        result = analyze_message(
            "My PIN is 4826.",
            self.model
        )

        self.assertEqual(
            result["decision"],
            "SENSITIVE"
        )

    def test_explicit_email(self):
        result = analyze_message(
            "My email is alex@example.com.",
            self.model
        )

        self.assertEqual(
            result["decision"],
            "SENSITIVE"
        )

    def test_context_pin_is_held(self):
        result = analyze_message(
            "For my debit card, the PIN I selected was 3917.",
            self.model
        )

        self.assertEqual(
            result["decision"],
            "REVIEW"
        )

        self.assertEqual(
            result["action"],
            "HOLD"
        )

    def test_context_account_is_held(self):
        result = analyze_message(
            "The account receiving the funds is 837261904553.",
            self.model
        )

        self.assertEqual(
            result["decision"],
            "REVIEW"
        )

    def test_result_structure(self):
        result = analyze_message(
            "How can I change my PIN?",
            self.model
        )

        required_keys = {
            "decision",
            "action",
            "reason",
            "ml_score",
            "detected_types",
        }

        self.assertTrue(
            required_keys.issubset(result.keys())
        )

    def test_no_raw_message_in_result(self):
        secret = "alex@example.com"

        result = analyze_message(
            f"My email is {secret}.",
            self.model
        )

        self.assertNotIn(
            secret,
            str(result)
        )


if __name__ == "__main__":
    unittest.main()
