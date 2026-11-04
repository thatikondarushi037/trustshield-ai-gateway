import json
import tempfile
import unittest
from pathlib import Path
from src.report_registry import file_hash, public_reports


class TestReportRegistry(unittest.TestCase):
    def test_missing_or_tampered_reports_are_not_served(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "reports").mkdir()
            self.assertEqual(public_reports(root)["reports"], {})
            path = root / "reports/holdout_preparation.json"
            data = {"status": "NOT_READY", "records": 0, "eligible_holdout_rows": 0, "blocking_findings": {"EMPTY": 1}, "private": "fictional-hidden-value"}
            path.write_text(json.dumps(data))
            (root / "reports/verified_manifest.json").write_text(json.dumps({"reports": {path.name: file_hash(path)}}))
            report = public_reports(root)
            self.assertEqual(len(report["reports"]), 1)
            self.assertNotIn("fictional-hidden-value", json.dumps(report))
            path.write_text("{}")
            self.assertEqual(public_reports(root)["reports"], {})
