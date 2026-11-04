
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import review_queue


class TestReviewQueue(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.db_patch = patch.object(
            review_queue,
            "DB_PATH",
            Path(self.temp_dir.name) / "reviews.db"
        )

        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_create_review(self):
        review_id = review_queue.create_review(
            "Uncertain privacy classification"
        )

        reviews = review_queue.list_reviews()

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["id"], review_id)
        self.assertEqual(reviews[0]["status"], "PENDING")

    def test_reject_review(self):
        review_id = review_queue.create_review(
            "Uncertain privacy classification"
        )

        success = review_queue.resolve_review(
            review_id, "REJECTED"
        )

        self.assertTrue(success)
        self.assertEqual(
            review_queue.list_reviews(),
            []
        )

    def test_cannot_resolve_twice(self):
        review_id = review_queue.create_review(
            "Uncertain privacy classification"
        )

        self.assertTrue(
            review_queue.resolve_review(
                review_id, "REJECTED"
            )
        )

        self.assertFalse(
            review_queue.resolve_review(
                review_id, "REWRITE_REQUESTED"
            )
        )

    def test_unknown_outcome_rejected(self):
        review_id = review_queue.create_review(
            "Uncertain privacy classification"
        )

        with self.assertRaises(ValueError):
            review_queue.resolve_review(
                review_id, "APPROVED"
            )

    def test_no_raw_prompt_storage(self):
        review_queue.create_review(
            "Uncertain privacy classification"
        )

        database = (
            Path(self.temp_dir.name) / "reviews.db"
        )

        self.assertNotIn(
            b"alex@example.com",
            database.read_bytes()
        )


if __name__ == "__main__":
    unittest.main()
