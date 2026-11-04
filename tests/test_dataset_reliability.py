import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import numpy as np

from src.dataset_reliability import (
    binary_metrics, check_report_privacy, evaluate_rows, live_consistency, markdown_report,
    review_pair, run_reliability, source_analysis,
)


def row(text, label="0", ref="fixture:1", **metadata):
    return dict(text=text, label=label, _ref=ref, **metadata)


class TestDatasetReliability(unittest.TestCase):
    def test_metrics_known_confusion_matrix(self):
        result = binary_metrics([0, 0, 1, 1], [0, 1, 0, 1])
        self.assertEqual(result["confusion_matrix"], [[1, 1], [1, 1]])
        for key in ("precision", "recall", "f1", "false_positive_rate", "false_negative_rate"):
            self.assertEqual(result[key], 0.5)

    def test_undefined_metrics_are_null_not_success(self):
        result = binary_metrics([0, 0], [0, 0])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["false_negative_rate"])
        self.assertEqual(result["false_positive_rate"], 0)
        self.assertEqual(binary_metrics([], [])["rows"], 0)

    def test_invalid_metrics_rejected(self):
        for actual, predicted in (([0], []), ([2], [0])):
            with self.assertRaises(ValueError):
                binary_metrics(actual, predicted)

    def test_near_pair_function_word_edit_is_likely_duplicate(self):
        a = "This fictional notification setting remains unchanged for the entire banking application."
        b = a[:-1] + ","
        result = review_pair(row(a), row(b, ref="fixture:2"))
        self.assertEqual(result["classification"], "LIKELY_DUPLICATE")
        self.assertNotIn(a, json.dumps(result))

    def test_negation_change_is_not_assumed_duplicate(self):
        a = "The fictional notification preferences should remain available in the banking application."
        b = a.replace("should remain", "should not remain")
        result = review_pair(row(a), row(b, ref="fixture:2"))
        self.assertEqual(result["classification"], "INCONCLUSIVE")
        self.assertTrue(result["negation_edit"])

    def test_source_missing_is_not_fabricated_as_verified_origin(self):
        result = source_analysis({"legacy": [row("fictional", "0"), row("sample", "1")],
                                  "observed": [row("example", "0", source="fixture_collection")]})
        self.assertEqual(result["observed"]["legacy"], {"NOT_RECORDED": {"0": 1, "1": 1}})
        self.assertEqual(result["observed"]["observed"], {"fixture_collection": {"0": 1}})

    def test_hybrid_hold_is_abstention_separate_from_ml_prediction(self):
        model = Mock()
        model.predict.return_value = np.array([0, 0, 1, 1])
        rows = [row("fictional secret value", "0", "fixture:1"),
                row("safe fixture", "0", "fixture:2"),
                row("sensitive fixture", "1", "fixture:3"),
                row("other fixture", "1", "fixture:4")]
        with patch("src.dataset_reliability.analyze_message", side_effect=[
            {"decision": d} for d in ("REVIEW", "SAFE", "SAFE", "SENSITIVE")
        ]):
            result, _ = evaluate_rows(rows, model)
        self.assertEqual(result["ml_only"]["confusion_matrix"], [[2, 0], [0, 2]])
        self.assertEqual(result["hybrid_non_safe"]["confusion_matrix"], [[1, 1], [1, 1]])
        self.assertEqual(result["hybrid_decision_matrix"], [[1, 1, 0], [1, 0, 1]])
        self.assertEqual(result["review_count"], 1)
        model.fit.assert_not_called()
        self.assertNotIn("fictional secret value", json.dumps(result))

    def test_invalid_rows_excluded_explicitly(self):
        model = Mock()
        result, _ = evaluate_rows([row("", "0"), row("fictional", "2")], model)
        self.assertEqual(result["excluded_rows"], 2)
        self.assertEqual(result["valid_rows"], 0)
        model.predict.assert_not_called()
        model.fit.assert_not_called()

    def test_live_comparison_detects_mismatch_without_raw_response(self):
        analysis = {"decision": "SAFE", "ml_score": 0.1, "detected_types": []}
        live = {"decision": "REVIEW", "ml_score": 0.8, "detected_types": []}
        with patch("src.dataset_reliability.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.post.return_value.json.return_value = live
            result = live_consistency([(row("fictional request"), analysis)], "http://127.0.0.1:8000")
        self.assertEqual(result["mismatches"], 1)
        self.assertEqual(result["mismatch_references"], ["fixture:1"])
        self.assertNotIn("fictional request", json.dumps(result))
        client.post.assert_called_once()

    def test_live_failure_does_not_export_exception(self):
        with patch("src.dataset_reliability.httpx.Client", side_effect=httpx.ConnectError("fictional-private-message")):
            result = live_consistency([], "http://127.0.0.1:8000")
        self.assertEqual(result["status"], "INCOMPLETE_SERVICE_OR_RESPONSE_ERROR")
        self.assertNotIn("fictional-private-message", json.dumps(result))
        with self.assertRaises(ValueError):
            live_consistency([], "http://example.com")

    def test_report_is_deterministic_aggregate_and_privacy_safe(self):
        model = Mock()
        model.predict.return_value = [0]
        secret = "fictional-sensitive-value-for-report-test"
        with patch("src.dataset_reliability.analyze_message", return_value={"decision": "SAFE"}):
            dataset, _ = evaluate_rows([row(secret)], model)
        report = {"pair_reviews": [], "source_analysis": source_analysis({}),
                  "datasets": {"fixture": dataset}, "live_consistency": {"status": "NOT_REQUESTED"}}
        output = markdown_report(report)
        self.assertEqual(output, markdown_report(report))
        self.assertNotIn(secret, output + json.dumps(report))
        self.assertIn("REVIEW", output)
        self.assertEqual(check_report_privacy(report, [row(secret)])["raw_text_matches"], 0)
        report["forbidden_field"] = secret
        with self.assertRaisesRegex(ValueError, "raw content is not displayed"):
            check_report_privacy(report, [row(secret)])

    def test_report_workflow_never_trains_or_replaces_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "config").mkdir()
            (root / "models").mkdir()
            artifact = root / "models/privacy_model_v02.joblib"
            artifact.write_bytes(b"fictional artifact fixture; loader mocked")
            data = root / "validation.csv"
            data.write_text("text,label\nfictional request,0\n")
            config = {"datasets": [{"id": "synthetic_validation", "path": "validation.csv",
                                    "group_namespace": "fixture"}]}
            (root / "config/dataset_audit.json").write_text(json.dumps(config))
            model = Mock()
            model.classes_ = np.array([0, 1])
            model.predict.return_value = [0]
            with patch("src.dataset_reliability.joblib.load", return_value=model), \
                    patch("src.dataset_reliability.analyze_message", return_value={"decision": "SAFE"}), \
                    patch("src.privacy_decision_engine.train_model", side_effect=AssertionError("Training prohibited")):
                first = run_reliability(root)
                self.assertEqual(first, run_reliability(root))
            model.fit.assert_not_called()
            self.assertEqual(artifact.read_bytes(), b"fictional artifact fixture; loader mocked")
            self.assertTrue(first["protected_inputs_unchanged"])
            self.assertNotIn("fictional request", json.dumps(first) + markdown_report(first))


if __name__ == "__main__":
    unittest.main()
