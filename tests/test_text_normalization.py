import unittest
from src.pii_rules import detect_pii
from src.secret_detector import detect_secrets
from src.redaction import redact_message
from src.policy_engine import enforce_policy


class TestNormalizationSafety(unittest.TestCase):
    def test_fullwidth_disclosure_and_secret_are_blocked(self):
        text = "Ｍｙ ＰＩＮ ｉｓ ４８２６."
        self.assertIn("PIN", [m["type"] for m in detect_pii(text)])
        key = "ａｐｉ＿ｋｅｙ ＝ ｆｉｃｔｉｏｎａｌ＿ｎｏｎｆｕｎｃｔｉｏｎａｌ＿ｋｅｙ"
        self.assertTrue(detect_secrets(key))
        result = enforce_policy(key, {"decision": "SAFE"})
        self.assertEqual(result["decision"], "BLOCK")

    def test_ligature_expansion_preserves_original_redaction_offsets(self):
        text = "Contact ﬁction@example.com for a fictional test."
        matches = detect_pii(text)
        email = next(m for m in matches if m["type"] == "EMAIL")
        self.assertEqual(text[email["start"]:email["end"]], "ﬁction@example.com")
        self.assertEqual(redact_message(text), "Contact [REDACTED] for a fictional test.")

    def test_newline_context_disclosure_is_held(self):
        text = "For my debit card,\nthe PIN I selected was\n3917."
        self.assertIn("PIN_CONTEXT", [m["type"] for m in detect_pii(text)])

    def test_plain_discussion_does_not_gain_a_pii_match(self):
        self.assertEqual(detect_pii("How can I safely change a PIN?"), [])
