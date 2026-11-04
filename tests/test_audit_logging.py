import sqlite3
import os
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from src import audit_logger, gateway_service
from src.api import app


class TestAuditLogging(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "audit.db"
        for module, name in ((audit_logger, "audit.db"),):
            patcher = patch.object(module, "DB_PATH", Path(folder.name) / name)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch("src.gateway_service.create_review", return_value="review-id")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.backend = Mock(return_value="response with confidential content")

    def gateway(self, classification="SAFE", text="Explain Python", types=None):
        with patch.object(gateway_service, "analyze_message", return_value={
            "decision": classification, "detected_types": types or []
        }):
            return gateway_service.process_request(text, None, self.backend)

    def test_committed_before_backend_and_completed_after(self):
        def backend(text):
            snapshot = audit_logger.monitoring_snapshot()
            self.assertEqual(snapshot["metrics"]["total"], 1)
            self.assertEqual(snapshot["records"][0]["execution_status"], "PENDING")
            return "ok"
        self.backend.side_effect = backend
        result = self.gateway()
        self.assertEqual(result["decision"], "ALLOW")
        record = audit_logger.monitoring_snapshot()["records"][0]
        self.assertEqual(record["id"], result["audit_id"])
        self.assertEqual(record["execution_status"], "SUCCEEDED")

    def test_block_hold_unknown_and_secret_are_audited(self):
        for classification, text in (("SENSITIVE", "private"), ("REVIEW", "uncertain"),
                                     ("UNKNOWN", "unexpected"),
                                     ("SAFE", "password = supersecret123")):
            self.gateway(classification, text)
        self.backend.assert_not_called()
        metrics = audit_logger.monitoring_snapshot()["metrics"]
        self.assertEqual(metrics["blocked"], 3)
        self.assertEqual(metrics["held"], 1)

    def test_no_sensitive_content_in_database_or_monitoring(self):
        self.gateway("SENSITIVE", "My email is unique@example.com", ["EMAIL"])
        self.gateway(text="password = supersecret123")
        self.gateway()
        serialized = str(audit_logger.monitoring_snapshot()).encode()
        for sensitive in (b"unique@example.com", b"supersecret123", b"Explain Python",
                          b"response with confidential content"):
            self.assertNotIn(sensitive, self.path.read_bytes())
            self.assertNotIn(sensitive, serialized)

    def test_untrusted_labels_and_decisions_rejected(self):
        for decision, types in (("prompt text", []), ("ALLOW", ["credential value"])):
            with self.assertRaises(ValueError):
                audit_logger.record_decision(decision, types, [])

    def test_insert_failure_prevents_execution(self):
        # A real filesystem/SQLite failure, rather than a successful mocked insert.
        with patch.object(audit_logger, "DB_PATH", self.path.parent):
            result = self.gateway()
        self.assertEqual(result["decision"], "ERROR")
        self.assertFalse(result["forward_allowed"])
        self.backend.assert_not_called()

    def test_locked_database_prevents_execution(self):
        audit_logger.monitoring_snapshot()
        with closing(sqlite3.connect(self.path)) as lock:
            lock.execute("BEGIN EXCLUSIVE")
            result = self.gateway()
            lock.rollback()
        self.assertEqual(result["decision"], "ERROR")
        self.backend.assert_not_called()

    def test_backend_failure_metadata_only(self):
        self.backend.side_effect = RuntimeError("credential in exception")
        result = self.gateway()
        self.assertEqual(result["decision"], "ERROR")
        snapshot = audit_logger.monitoring_snapshot()
        self.assertEqual(snapshot["metrics"]["failed"], 1)
        self.assertNotIn("credential in exception", str(snapshot) + str(result))

    def test_completion_failure_does_not_claim_success_or_retry(self):
        with patch.object(gateway_service, "record_outcome", side_effect=sqlite3.OperationalError):
            result = self.gateway()
        self.assertEqual(result["decision"], "ERROR")
        self.assertTrue(result["backend_called"])
        self.assertIsNone(result["response"])
        self.backend.assert_called_once()
        self.assertEqual(audit_logger.monitoring_snapshot()["metrics"]["pending"], 1)

    def test_review_failure_remains_closed(self):
        with patch.object(gateway_service, "create_review", side_effect=sqlite3.OperationalError):
            result = self.gateway("REVIEW")
        self.assertEqual(result["decision"], "ERROR")
        self.backend.assert_not_called()
        self.assertEqual(audit_logger.monitoring_snapshot()["metrics"]["failed"], 1)

    def test_connections_closed_and_concurrent_writes_persist(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _: audit_logger.record_decision("BLOCK", [], []), range(20)))
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(audit_logger.monitoring_snapshot(3)["metrics"]["total"], 20)
        self.assertEqual(len(audit_logger.monitoring_snapshot(3)["records"]), 3)
        # Windows refuses this if any SQLite connection remains open.
        self.path.rename(self.path.with_suffix(".moved"))

    def test_api_monitoring_validation_and_unavailable(self):
        client = TestClient(app, client=("127.0.0.1", 50000),
                            headers={"Authorization": "Bearer fictional-test-token"})
        token_patch = patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": "fictional-test-token"})
        token_patch.start()
        self.addCleanup(token_patch.stop)
        self.gateway()
        self.assertEqual(client.get("/audit").json()["metrics"]["total"], 1)
        self.assertEqual(client.get("/audit?limit=201").status_code, 422)
        with patch("src.api.monitoring_snapshot", side_effect=RuntimeError("private path")):
            response = client.get("/audit")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private path", response.text)

    def test_monitoring_requires_token_and_local_peer(self):
        local = TestClient(app, client=("127.0.0.1", 50000))
        with patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": "fictional-test-token"}):
            self.assertEqual(local.get("/audit").status_code, 401)
            self.assertEqual(local.get("/audit", headers={"Authorization": "Bearer wrong"}).status_code, 401)
            remote = TestClient(app, client=("192.0.2.1", 50000))
            response = remote.get("/audit", headers={
                "Authorization": "Bearer fictional-test-token", "X-Forwarded-For": "127.0.0.1"})
            self.assertEqual(response.status_code, 403)
        with patch.dict(os.environ, {"TRUSTSHIELD_AUDIT_TOKEN": ""}):
            self.assertEqual(local.get("/audit").status_code, 503)

    def test_finalized_metadata_for_every_gateway_outcome(self):
        for classification in ("SAFE", "SENSITIVE", "REVIEW"):
            with self.subTest(classification=classification):
                result = self.gateway(classification)
                row = next(row for row in audit_logger.monitoring_snapshot()["records"]
                           if row["id"] == result["audit_id"])
                expected = int(classification == "SAFE")
                self.assertEqual(row["backend_attempted"], expected)
                self.assertEqual(row["backend_succeeded"], expected)
                self.assertIsNotNone(row["completed_at"])
                self.assertGreaterEqual(row["latency_ms"], 0)

    def test_denied_finalization_failure_remains_closed(self):
        for classification in ("SENSITIVE", "REVIEW"):
            with patch.object(gateway_service, "record_outcome", side_effect=sqlite3.OperationalError):
                result = self.gateway(classification)
            self.assertEqual(result["decision"], "ERROR")
            self.assertFalse(result["forward_allowed"])
        self.backend.assert_not_called()

    def test_existing_gateway_routes_use_audit_gate(self):
        client = TestClient(app)
        with patch.object(gateway_service, "analyze_message", return_value={
            "decision": "SAFE", "detected_types": []
        }), patch.object(gateway_service, "record_decision", side_effect=sqlite3.OperationalError), \
                patch("src.api.generate_local_response") as local:
            for route in ("/gateway", "/gateway/local"):
                response = client.post(route, json={"text": "Explain Python"})
                self.assertEqual(response.json()["decision"], "ERROR")
            local.assert_not_called()
        self.assertEqual(client.get("/health").status_code, 200)

    def test_outcome_cannot_be_overwritten(self):
        record_id = audit_logger.record_decision("ALLOW", [], [])
        audit_logger.record_outcome(record_id, "SUCCEEDED")
        with self.assertRaises(ValueError):
            audit_logger.record_outcome(record_id, "FAILED")
