import unittest
import numpy as np
from unittest.mock import patch
from src.ml_experiments import probability_quality, logit, ensure_separation, selective_metrics
from src.contextual_adapter import OllamaEncoder
from src.robustness import development_probes


class TestMLExperiments(unittest.TestCase):
    def test_probability_scores_and_bins(self):
        result = probability_quality([0, 1], [0, 1])
        self.assertEqual(result["brier_score"], 0)
        self.assertEqual(result["expected_calibration_error"], 0)
        self.assertEqual(sum(b["count"] for b in result["reliability_bins"]), 2)
        self.assertTrue(np.isfinite(logit(np.array([0., 1.]))).all())

    def test_invalid_probabilities_rejected(self):
        for p in ([float("nan")], [1.1], []):
            with self.assertRaises(ValueError):
                probability_quality([1], p)

    def test_calibration_leakage_blocks(self):
        row = {"text": "fictional duplicated calibration record", "label": "0", "_namespace": "x", "_ref": "x:1"}
        with self.assertRaises(ValueError):
            ensure_separation([row], [dict(row, _ref="y:1")])
        with self.assertRaises(ValueError):
            ensure_separation([dict(row, template_id="family")], [dict(row, text="completely different text", template_id="family")])

    def test_selective_forward_coverage_is_monotonic(self):
        rows = [{"text": "Explain fictional astronomy", "label": "0"}, {"text": "Describe fictional particles", "label": "1"}]
        low = selective_metrics(rows, [.35, .55], .3)
        high = selective_metrics(rows, [.35, .55], .6)
        self.assertEqual(low["automatic_forward_coverage"], 0)
        self.assertIsNone(low["accepted_request_error_rate"])
        self.assertEqual(high["automatic_forward_coverage"], 1)
        self.assertEqual(high["accepted_request_error_rate"], .5)

    def test_robustness_is_development_only_and_has_ambiguous_cases(self):
        cases = development_probes()
        self.assertEqual(len(cases), 80)
        self.assertTrue(any(c["privacy_label"] is None for c in cases))
        self.assertTrue(any(c["privacy_label"] != c["withholding_label"] for c in cases))
        self.assertTrue(all(len(c["text"]) <= 20000 for c in cases))

    def test_encoder_response_validation_and_no_silent_truncation(self):
        with patch("src.contextual_adapter.httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.post.return_value.json.return_value = {"embeddings": [[float("nan")]]}
            with self.assertRaises(ValueError):
                OllamaEncoder().encode(["fictional"])
            self.assertFalse(client.post.call_args.kwargs["json"]["truncate"])
