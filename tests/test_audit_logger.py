"""Storage tests independent of FastAPI, model training, or Ollama."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src import audit_logger


class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "audit.db"
        patcher = patch.object(audit_logger, "DB_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_create_finish_and_aggregate_latency(self):
        first = audit_logger.record_decision("ALLOW", [], [])
        second = audit_logger.record_decision("ALLOW", [], [])
        pending = audit_logger.monitoring_snapshot()["records"][0]
        self.assertIsNone(pending["backend_attempted"])
        audit_logger.record_outcome(first, "SUCCEEDED", 20)
        audit_logger.record_outcome(second, "FAILED", 40)
        metrics = audit_logger.monitoring_snapshot()["metrics"]
        self.assertEqual(metrics["average_latency_ms"], 30)
        self.assertEqual(metrics["backend_attempted"], 2)
        self.assertEqual(metrics["backend_succeeded"], 1)
        self.assertEqual(metrics["failed"], 1)

    def test_invalid_finalization_leaves_record_pending(self):
        record_id = audit_logger.record_decision("ALLOW", [], [])
        for latency in (-1, float("nan"), float("inf"), True, "private text"):
            with self.subTest(latency=latency), self.assertRaises(ValueError):
                audit_logger.record_outcome(record_id, "SUCCEEDED", latency)
        with self.assertRaises(ValueError):
            audit_logger.record_outcome(record_id, "NOT_ALLOWED", 1)
        self.assertEqual(audit_logger.monitoring_snapshot()["metrics"]["pending"], 1)

    def test_block_and_hold_finalize_once_without_backend(self):
        for decision in ("BLOCK", "HOLD"):
            record_id = audit_logger.record_decision(decision, [], [])
            audit_logger.record_outcome(record_id, "NOT_ALLOWED", 5)
            with self.assertRaises(ValueError):
                audit_logger.record_outcome(record_id, "NOT_ALLOWED", 6)
        for row in audit_logger.monitoring_snapshot()["records"]:
            self.assertEqual(row["backend_attempted"], 0)
            self.assertEqual(row["backend_succeeded"], 0)
            self.assertIsNotNone(row["completed_at"])

    def test_transaction_failure_rolls_back_and_closes_connection(self):
        audit_logger.monitoring_snapshot()
        with self.assertRaises(RuntimeError):
            with audit_logger.connect_db() as connection:
                connection.execute("""INSERT INTO audit_records
                    (id, created_at, decision, detected_types, secret_types, execution_status)
                    VALUES ('test-id','2026-01-01','BLOCK','[]','[]','NOT_ALLOWED')""")
                raise RuntimeError("simulated failure")
        self.assertEqual(audit_logger.monitoring_snapshot()["metrics"]["total"], 0)
        self.path.rename(self.path.with_suffix(".closed"))

    def test_existing_schema_is_migrated_without_fabricating_measurements(self):
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("""CREATE TABLE audit_records (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, decision TEXT NOT NULL,
                    detected_types TEXT NOT NULL, secret_types TEXT NOT NULL,
                    execution_status TEXT NOT NULL, completed_at TEXT)""")
                connection.execute("""INSERT INTO audit_records VALUES
                    ('legacy-id','2026-01-01','ALLOW','[]','[]','SUCCEEDED','2026-01-01')""")
        row = audit_logger.monitoring_snapshot()["records"][0]
        self.assertEqual(row["id"], "legacy-id")
        for field in ("latency_ms", "backend_attempted", "backend_succeeded"):
            self.assertIsNone(row[field])
        audit_logger.record_decision("BLOCK", [], [])
        self.assertEqual(audit_logger.monitoring_snapshot()["metrics"]["total"], 2)

    def test_unknown_secret_labels_are_never_persisted(self):
        with self.assertRaises(ValueError):
            audit_logger.record_decision("BLOCK", [], ["fictional-password-value"])
        self.assertFalse(self.path.exists())
