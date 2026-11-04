import json
import atexit
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.app_test import TMP_DIR

# Streamlit creates a process-global temporary directory; close it explicitly on
# Windows instead of letting weakref cleanup emit an atexit ResourceWarning.
atexit.register(TMP_DIR.cleanup)


class TestDashboard(unittest.TestCase):
    def run_page(self, page, response=None):
        with patch("src.console_client.safe_get", return_value=response):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "dashboard.py"), default_timeout=20).run()
            app.sidebar.radio[0].set_value(page).run()
        self.assertEqual(len(app.exception), 0)
        return app

    def test_all_sections_have_safe_unavailable_states(self):
        for page in ("Security analytics", "Review queue", "ML evaluation", "System health"):
            with self.subTest(page=page):
                app = self.run_page(page)
                self.assertGreater(len(app.warning), 0)

    def test_analytics_counts_and_empty_chart(self):
        response = {"metrics": {"total": 0, "allowed": 0, "blocked": 0, "held": 0,
                                "backend_attempted": 0, "backend_succeeded": 0, "pending": 0,
                                "failed": 0, "average_latency_ms": None}, "records": []}
        app = self.run_page("Security analytics", response)
        self.assertEqual([m.value for m in app.metric][:4], ["0", "0", "0", "0"])
        self.assertTrue(any("No audited" in item.value for item in app.info))

    def test_review_metadata_has_no_approval_action(self):
        app = self.run_page("Review queue", {"records": [{"id": "fixture-ticket", "status": "PENDING", "created_at": "2026-01-01", "resolved_at": None}]})
        self.assertEqual(len(app.dataframe[0].value), 1)
        self.assertFalse(any("Approve" in b.label for b in app.button))

    def test_draft_checks_never_call_gateway(self):
        with patch("src.console_client.api_request", return_value={"decision": "BLOCK", "reason": "Credential pattern", "preview_only": True}) as request:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "dashboard.py"), default_timeout=20).run()
            app.checkbox[0].check().run()
            app.text_area[0].input("api_key = fictional_nonfunctional_ui_key").run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(request.called)
            self.assertTrue(all(call.args[1] == "/preview" for call in request.call_args_list))
            self.assertTrue(any("Draft check: BLOCK" in item.value for item in app.info))

    def test_submit_rechecks_server_instead_of_trusting_preview(self):
        response = {"decision": "HOLD", "reason": "Manual review required", "backend_called": False,
                    "response": None, "detected_types": [], "secret_types": [], "review_id": "fixture-ticket"}
        with patch("src.console_client.api_request", return_value=response) as request:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "dashboard.py"), default_timeout=20).run()
            app.text_area[0].input("Fictional contextual request").run()
            app.button[0].click().run()  # main-area submit; sidebar button is separate
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any(call.args[1] == "/gateway/local" for call in request.call_args_list))
            self.assertTrue(any("HOLD" in item.value for item in app.warning))

    def test_verified_ml_tables_render_with_limitations(self):
        metric = {"precision": .5, "recall": .5, "f1": .5, "false_positive_rate": .5,
                  "false_negative_rate": .5, "confusion_matrix": [[1, 1], [1, 1]]}
        response = {"reports": {"dataset_reliability.json": {"datasets": {"fixture": {
            "ml_only": metric, "hybrid_non_safe": metric, "hybrid_decision_matrix": [[1, 1, 0], [1, 0, 1]]}}}}}
        app = self.run_page("ML evaluation", response)
        self.assertEqual(len(app.metric), 5)
        self.assertEqual(len(app.dataframe), 2)
        self.assertTrue(any("NOT READY" in warning.value for warning in app.warning))

    def test_service_health_renders_actual_status_values(self):
        app = self.run_page("System health", {"api": "UP", "ollama": "UP", "generation_model": "UNAVAILABLE", "audit": "UP", "reviews": "UP"})
        self.assertEqual([m.value for m in app.metric], ["UP", "UP", "UNAVAILABLE", "UP", "UP"])
