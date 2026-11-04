"""Metadata-only security journal. No request/response text is accepted."""

import json
import math
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.pii_rules import PII_PATTERNS, CONTEXT_PATTERNS
from src.secret_detector import SECRET_PATTERNS
from src.settings import data_directory

DB_PATH = data_directory() / "audit.db"


@contextmanager
def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=5.0)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            # Serialize schema checks/migrations and keep multi-query reads consistent.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS audit_records (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK(decision IN ('ALLOW','BLOCK','HOLD')),
                    detected_types TEXT NOT NULL,
                    secret_types TEXT NOT NULL,
                    execution_status TEXT NOT NULL CHECK(execution_status IN
                        ('NOT_ALLOWED','PENDING','SUCCEEDED','FAILED','REVIEW_FAILED')),
                    completed_at TEXT
                )
            """)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(audit_records)")}
            for name, declaration in (
                ("latency_ms", "REAL CHECK(latency_ms >= 0)"),
                ("backend_attempted", "INTEGER CHECK(backend_attempted IN (0,1))"),
                ("backend_succeeded", "INTEGER CHECK(backend_succeeded IN (0,1))"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE audit_records ADD COLUMN {name} {declaration}")
            yield connection
    finally:
        connection.close()


def record_decision(decision: str, detected_types: list, secret_types: list) -> str:
    if decision not in {"ALLOW", "BLOCK", "HOLD"}:
        raise ValueError("Invalid audit decision")
    # Reject unknown labels rather than accidentally persisting supplied text.
    if (not set(detected_types) <= (PII_PATTERNS.keys() | CONTEXT_PATTERNS.keys())
            or not set(secret_types) <= SECRET_PATTERNS.keys()):
        raise ValueError("Invalid audit detection label")
    record_id = str(uuid.uuid4())
    with connect_db() as connection:
        connection.execute(
            """INSERT INTO audit_records
               (id, created_at, decision, detected_types, secret_types, execution_status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record_id, datetime.now(timezone.utc).isoformat(), decision,
             json.dumps(sorted(set(detected_types))),
             json.dumps(sorted(set(secret_types))),
             "PENDING" if decision == "ALLOW" else "NOT_ALLOWED"),
        )
    # The transaction has committed and the connection is closed at this point.
    return record_id


def record_outcome(record_id: str, status: str, latency_ms: float = 0.0):
    if status not in {"SUCCEEDED", "FAILED", "REVIEW_FAILED", "NOT_ALLOWED"}:
        raise ValueError("Invalid audit outcome")
    if (isinstance(latency_ms, bool) or not isinstance(latency_ms, (int, float))
            or not math.isfinite(latency_ms) or latency_ms < 0):
        raise ValueError("Invalid audit latency")
    attempted = int(status in {"SUCCEEDED", "FAILED"})
    succeeded = int(status == "SUCCEEDED")
    with connect_db() as connection:
        cursor = connection.execute(
            """UPDATE audit_records SET execution_status = ?, completed_at = ?,
               latency_ms = ?, backend_attempted = ?, backend_succeeded = ?
               WHERE id = ? AND completed_at IS NULL AND
               ((execution_status = 'PENDING' AND ? IN ('SUCCEEDED','FAILED')) OR
                (decision = 'HOLD' AND execution_status = 'NOT_ALLOWED'
                 AND ? = 'REVIEW_FAILED') OR
                (decision IN ('BLOCK','HOLD') AND execution_status = 'NOT_ALLOWED'
                 AND ? = 'NOT_ALLOWED'))""",
            (status, datetime.now(timezone.utc).isoformat(), latency_ms,
             attempted, succeeded, record_id, status, status, status),
        )
        if cursor.rowcount != 1:
            raise ValueError("Audit outcome transition rejected")


def monitoring_snapshot(limit: int = 50) -> dict:
    if not 1 <= limit <= 200:
        raise ValueError("Invalid audit limit")
    with connect_db() as connection:
        counts = connection.execute(
            """SELECT COUNT(*) AS total,
               COALESCE(SUM(decision = 'ALLOW'),0) AS allowed,
               COALESCE(SUM(decision = 'BLOCK'),0) AS blocked,
               COALESCE(SUM(decision = 'HOLD'),0) AS held,
               COALESCE(SUM(execution_status = 'PENDING'),0) AS pending,
               COALESCE(SUM(execution_status IN ('FAILED','REVIEW_FAILED')),0) AS failed,
               AVG(latency_ms) AS average_latency_ms,
               COALESCE(SUM(backend_attempted = 1),0) AS backend_attempted,
               COALESCE(SUM(backend_succeeded = 1),0) AS backend_succeeded
               FROM audit_records"""
        ).fetchone()
        rows = connection.execute(
            "SELECT * FROM audit_records ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    records = [dict(row) for row in rows]
    for record in records:
        for field in ("detected_types", "secret_types"):
            record[field] = json.loads(record[field])
    return {"metrics": dict(counts), "records": records}
