import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.api import app
from src import audit_logger, review_queue
from src.gateway_service import process_request
from src.settings import MAX_BODY_BYTES, monitoring_token


class TestReleaseSecurity(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for module, name in ((audit_logger, "audit.db"), (review_queue, "reviews.db")):
            p = patch.object(module, "DB_PATH", Path(directory.name) / name)
            p.start(); self.addCleanup(p.stop)
        self.client = TestClient(app, client=("127.0.0.1", 50001))

    def test_validation_never_echoes_private_payload(self):
        secret = "fictional-private-validation-value"
        for data in ({"text": {"private": secret}}, {"text": 123, "extra": secret}, {"text": " "}, {"text": "\x00"}):
            response = self.client.post("/gateway", json=data)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(secret, response.text)

    def test_size_limits_are_enforced_before_analysis(self):
        with patch("src.api.analyze_message") as analyze, patch("src.api.process_request") as process:
            response = self.client.post("/gateway", json={"text": "x" * 20001})
            self.assertEqual(response.status_code, 422)
            response = self.client.post("/gateway", content=b"x" * (MAX_BODY_BYTES + 1))
            self.assertEqual(response.status_code, 413)
            response = self.client.post("/gateway", content=iter([b"x" * 50000, b"y" * 50000]))
            self.assertEqual(response.status_code, 413)
            process.assert_not_called(); analyze.assert_not_called()

    def test_analysis_failure_never_calls_backend(self):
        backend = Mock()
        with patch("src.gateway_service.analyze_message", side_effect=RuntimeError("fictional-private-exception")):
            result = process_request("fictional", None, backend)
        self.assertEqual(result["decision"], "ERROR")
        self.assertNotIn("fictional-private-exception", str(result))
        backend.assert_not_called()

    def test_inconsistent_policy_never_calls_backend(self):
        backend = Mock()
        with patch("src.gateway_service.analyze_message", return_value={"decision": "SAFE", "detected_types": []}), \
             patch("src.gateway_service.enforce_policy", return_value={"decision": "BLOCK", "forward_allowed": True}):
            result = process_request("fictional", None, backend)
        self.assertEqual(result["decision"], "ERROR")
        backend.assert_not_called()

    def test_preview_never_executes_or_writes_audit(self):
        with patch("src.api.generate_local_response") as backend:
            response = self.client.post("/preview", json={"text": "api_key = fictional_nonfunctional_preview_key"})
        self.assertEqual(response.json()["decision"], "BLOCK")
        self.assertTrue(response.json()["preview_only"])
        self.assertFalse(response.json()["forward_allowed"])
        backend.assert_not_called()
        self.assertFalse(audit_logger.DB_PATH.exists())

    def test_unhandled_exception_has_no_secret_or_traceback(self):
        with patch("src.api.analyze_message", side_effect=RuntimeError("fictional-private-exception")):
            response = self.client.post("/analyze", json={"text": "fictional"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("fictional-private-exception", response.text)
        self.assertNotIn("Traceback", response.text)

    def test_operational_endpoints_require_authentication(self):
        with patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": "fictional-local-token", "TRUSTSHIELD_AUDIT_TOKEN_FILE": ""}):
            for path in ("/reviews", "/reports", "/operations/health"):
                self.assertEqual(self.client.get(path).status_code, 401)
            response = self.client.get("/reviews", headers={"Authorization": "Bearer fictional-local-token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["records"], [])

    def test_file_secret_and_ambiguous_configuration(self):
        path = review_queue.DB_PATH.parent / "token"
        path.write_text("fictional-file-token\n")
        with patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": "", "TRUSTSHIELD_AUDIT_TOKEN_FILE": str(path)}):
            self.assertEqual(monitoring_token(), "fictional-file-token")
            with patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": "also-configured"}):
                with self.assertRaises(ValueError):
                    monitoring_token()

    def test_review_visibility_strips_freeform_reason(self):
        review_queue.create_review("fictional-private-reason")
        with patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": "fictional-local-token", "TRUSTSHIELD_AUDIT_TOKEN_FILE": ""}):
            response = self.client.get("/reviews", headers={"Authorization": "Bearer fictional-local-token"})
        self.assertNotIn("fictional-private-reason", response.text)
        self.assertNotIn("reason", response.json()["records"][0])

    def test_docker_network_is_explicit_and_still_authenticated(self):
        client = TestClient(app, client=("172.29.77.5", 50000))
        with patch.dict(os.environ, {"TRUSTSHIELD_MONITORING_CIDRS": "172.29.77.0/24",
                                    "TRUSTSHIELD_AUDIT_TOKEN": "fictional-local-token", "TRUSTSHIELD_AUDIT_TOKEN_FILE": ""}):
            self.assertEqual(client.get("/reviews").status_code, 401)
            self.assertEqual(client.get("/reviews", headers={"Authorization": "Bearer fictional-local-token"}).status_code, 200)
