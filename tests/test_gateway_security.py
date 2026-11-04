
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from src.gateway_service import process_request


class TestGatewaySecurity(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for module in ("src.audit_logger", "src.review_queue"):
            patcher = patch(module + ".DB_PATH", Path(folder.name) / (module.split(".")[-1] + ".db"))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.backend = Mock(return_value="Backend OK")

    def run_gateway(self, text, classification):
        analysis = {
            "decision": classification,
            "detected_types": [],
        }

        with patch(
            "src.gateway_service.analyze_message",
            return_value=analysis
        ):
            return process_request(
                text, None, self.backend
            )

    def test_secret_is_blocked(self):
        result = self.run_gateway(
            "api_key = abcdefghijklmnopqrstuvwxyz",
            "SAFE",
        )

        self.assertEqual(result["decision"], "BLOCK")
        self.assertFalse(result["forward_allowed"])
        self.backend.assert_not_called()

    def test_sensitive_message_is_blocked(self):
        result = self.run_gateway(
            "My email is alex@example.com",
            "SENSITIVE",
        )

        self.assertEqual(result["decision"], "BLOCK")
        self.backend.assert_not_called()

    def test_review_is_held(self):
        result = self.run_gateway(
            "Please check my account details",
            "REVIEW",
        )

        self.assertEqual(result["decision"], "HOLD")
        self.backend.assert_not_called()

    def test_safe_request_is_forwarded(self):
        result = self.run_gateway(
            "Explain machine learning",
            "SAFE",
        )

        self.assertEqual(result["decision"], "ALLOW")
        self.backend.assert_called_once()
        self.assertEqual(result["response"], "Backend OK")

    def test_unknown_decision_is_blocked(self):
        result = self.run_gateway(
            "Some unexpected input",
            "UNKNOWN",
        )

        self.assertEqual(result["decision"], "BLOCK")
        self.backend.assert_not_called()

    def test_backend_failure_is_controlled(self):
        self.backend.side_effect = RuntimeError(
            "Internal backend failure"
        )

        result = self.run_gateway(
            "Explain Python functions",
            "SAFE",
        )

        self.assertEqual(result["decision"], "ERROR")
        self.assertFalse(result["forward_allowed"])
        self.assertIsNone(result["response"])
        self.assertNotIn(
            "Internal backend failure",
            str(result)
        )


if __name__ == "__main__":
    unittest.main()
