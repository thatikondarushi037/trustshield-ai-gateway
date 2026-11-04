
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from contextlib import contextmanager
from src.settings import data_directory

DB_PATH = data_directory() / "reviews.db"

VALID_OUTCOMES = {"REJECTED", "REWRITE_REQUESTED"}



@contextmanager
def connect_db():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        with connection:
            yield connection
    finally:
        connection.close()



def initialize_db():

    with connect_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)


def create_review(reason: str) -> str:
    initialize_db()

    review_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO reviews
            (id, status, reason, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                review_id,
                "PENDING",
                reason,
                created_at,
            ),
        )

    return review_id


def list_reviews(status: str = "PENDING", limit: int = 100) -> list[dict]:
    if status not in {"PENDING", *VALID_OUTCOMES} or not 1 <= limit <= 200:
        raise ValueError("Invalid review filter")
    initialize_db()

    with connect_db() as connection:
        rows = connection.execute(
            """
            SELECT id, status, reason, created_at, resolved_at
            FROM reviews
            WHERE status = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (status, limit),
        ).fetchall()

    return [dict(row) for row in rows]


def resolve_review(review_id: str, outcome: str) -> bool:
    if outcome not in VALID_OUTCOMES:
        raise ValueError("Invalid review outcome")

    initialize_db()

    resolved_at = datetime.now(timezone.utc).isoformat()

    with connect_db() as connection:
        cursor = connection.execute(
            """
            UPDATE reviews
            SET status = ?, resolved_at = ?
            WHERE id = ? AND status = 'PENDING'
            """,
            (outcome, resolved_at, review_id),
        )

    return cursor.rowcount == 1
