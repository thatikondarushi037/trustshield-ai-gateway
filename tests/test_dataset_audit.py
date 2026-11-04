import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.dataset_audit import (
    duplicate_stats, inventory, literal_assignment, load_dataset, markdown_report,
    near_duplicates, normalize, overlap, run_audit,
)


def rows(*items, namespace="fixture", dataset="fixture"):
    return [dict(item, _ref=f"{dataset}:{i}", _namespace=namespace)
            for i, item in enumerate(items, 1)]


class TestDatasetAudit(unittest.TestCase):
    def test_exact_duplicates_and_conflicts_are_distinct(self):
        data = rows({"text": "fictional sample", "label": "0"},
                    {"text": "fictional sample", "label": "1"},
                    {"text": "another sample", "label": "0"},
                    {"text": "another sample", "label": "0"})
        result = duplicate_stats(data)
        self.assertEqual(result["duplicate_groups"], 2)
        self.assertEqual(result["excess_rows"], 2)
        self.assertEqual(result["conflicting_label_groups"], 1)
        self.assertNotIn("fictional sample", json.dumps(result))

    def test_normalization_is_explicit_and_preserves_punctuation(self):
        self.assertEqual(normalize("  ＡLPHA\tBeta  "), "alpha beta")
        self.assertNotEqual(normalize("alpha!"), normalize("alpha"))
        data = rows({"text": "Alpha  Beta", "label": "0"},
                    {"text": "alpha beta", "label": "1"})
        self.assertEqual(duplicate_stats(data)["conflicting_label_groups"], 0)
        self.assertEqual(duplicate_stats(data, canonical=True)["conflicting_label_groups"], 1)

    def test_invalid_rows_and_missing_source_are_visible(self):
        data = rows({"text": "", "label": "0"}, {"text": "hello", "label": "private-value"})
        result = inventory(data, ["text", "label"])
        self.assertEqual(result["missing_or_blank_text"], 1)
        self.assertEqual(result["invalid_or_missing_labels"], 1)
        self.assertEqual(result["source_missing_rows"], 2)
        self.assertNotIn("private-value", json.dumps(result))
        self.assertEqual(inventory([], ["text"])["missing_required_columns"], ["label"])

    def test_leaked_text_and_conflicting_cross_split_labels(self):
        a = rows({"text": "deliberately reused fixture", "label": "0"}, dataset="train")
        b = rows({"text": "deliberately reused fixture", "label": "1"}, dataset="validation")
        result = overlap(a, b)
        self.assertEqual(result["exact"]["shared_texts"], 1)
        self.assertEqual(result["exact"]["conflicting_label_texts"], 1)
        self.assertEqual(result["exact"]["examples"][0], {"left": "train:1", "right": "validation:1"})

    def test_template_group_leak_without_shared_text(self):
        a = rows({"text": "first variant", "label": "0", "template_id": "family_a"})
        b = rows({"text": "second variant", "label": "1", "template_id": "family_a"})
        result = overlap(a, b)
        self.assertEqual(result["exact"]["shared_texts"], 0)
        self.assertEqual(result["groups"]["template_id"]["shared_groups"], 1)

    def test_unrelated_local_group_ids_do_not_collide(self):
        a = rows({"text": "a", "label": "0", "group_id": "0"}, namespace="pilot")
        b = rows({"text": "b", "label": "1", "group_id": "0"}, namespace="hard")
        result = overlap(a, b)["groups"]["group_id"]
        self.assertFalse(result["comparable_namespace"])
        self.assertIsNone(result["shared_groups"])

    def test_shared_source_is_not_a_document_group(self):
        a = rows({"text": "a", "label": "0", "source": "publisher"})
        b = rows({"text": "b", "label": "1", "source": "publisher"})
        result = overlap(a, b)
        self.assertEqual(result["shared_source_collections"], 1)
        self.assertIsNone(result["groups"]["source_group"]["shared_groups"])

    def test_document_source_group_overlap_and_partial_metadata(self):
        a = rows({"text": "first", "label": "0", "source_group": "document_a"},
                 {"text": "untracked", "label": "0"})
        b = rows({"text": "second", "label": "1", "source_group": "document_a"})
        result = overlap(a, b)["groups"]["source_group"]
        self.assertEqual(result["shared_groups"], 1)
        self.assertEqual(result["left_missing_rows"], 1)

    def test_near_candidates_are_not_exact_leakage(self):
        a = rows({"text": "Please explain the fictional banking notification preferences carefully.", "label": "0"}, dataset="train")
        b = rows({"text": "Please explain the fictional banking notification preferences carefully!", "label": "1"}, dataset="validation")
        result = near_duplicates(a, b, threshold=0.8, batch_size=1)
        self.assertEqual(result["candidate_text_pairs"], 1)
        self.assertEqual(result["opposite_label_text_pairs"], 1)
        self.assertEqual(overlap(a, b)["exact"]["shared_texts"], 0)
        self.assertNotIn("banking", json.dumps(result))

    def test_near_counts_unique_text_pairs_and_expands_row_multiplicity(self):
        data = rows({"text": "synthetic lengthy notification preferences", "label": "0"},
                    {"text": "synthetic lengthy notification preferences", "label": "0"},
                    {"text": "synthetic lengthy notification preferences!", "label": "0"})
        first = near_duplicates(data, threshold=0.8, batch_size=1)
        second = near_duplicates(data, threshold=0.8, batch_size=20)
        self.assertEqual(first, second)
        self.assertEqual(first["candidate_text_pairs"], 1)
        self.assertEqual(first["candidate_row_pairs"], 2)

    def test_empty_and_unrelated_texts(self):
        self.assertEqual(near_duplicates([])["candidate_text_pairs"], 0)
        data = rows({"text": "astronomy telescope", "label": "0"},
                    {"text": "cooking noodles", "label": "1"})
        self.assertEqual(near_duplicates(data)["candidate_text_pairs"], 0)
        for threshold in (-1, 0, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                near_duplicates(data, threshold=threshold)

    def test_sample_cap_does_not_truncate_candidate_counts(self):
        data = rows(*({"text": f"fictional long notification preference setting {suffix}", "label": "0"}
                      for suffix in ("a", "b", "c")))
        result = near_duplicates(data, threshold=0.7, sample_limit=1, batch_size=1)
        self.assertEqual(result["candidate_text_pairs"], 3)
        self.assertEqual(len(result["examples"]), 1)

    def test_ast_extraction_never_executes_module(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "danger.py"
            path.write_text("raise RuntimeError('must not execute')\nEXAMPLES = [('synthetic', 0)]\n")
            self.assertEqual(literal_assignment(path, "EXAMPLES"), [("synthetic", 0)])
            path.write_text("EXAMPLES = dangerous_call()\n")
            with self.assertRaises(ValueError):
                literal_assignment(path, "EXAMPLES")

    def test_report_is_deterministic_private_and_classifies_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, values in (("train", [("fictional_email@example.com", "0", "shared")]),
                                 ("validation", [("fictional_email@example.com", "1", "different"),
                                                 ("unrelated string", "0", "shared")])):
                with (root / f"{name}.csv").open("w", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["text", "label", "template_id"])
                    writer.writerows(values)
            specs = [{"id": name, "path": f"{name}.csv", "role": role,
                      "origin": "fixture", "group_namespace": "fixture"}
                     for name, role in (("train", "train"), ("validation", "evaluation"))]
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"datasets": specs, "boundaries": [["train", "validation"]],
                                            "near_comparisons": [], "provenance_files": []}))
            first = run_audit(root, manifest)
            self.assertEqual(first, run_audit(root, manifest))
            self.assertEqual(first["comparisons"][0]["interpretation"], "DEFINITE_TEXT_CONTAMINATION")
            serialized = json.dumps(first) + markdown_report(first)
            self.assertNotIn("fictional_email@example.com", serialized)
            self.assertNotIn("unrelated string", serialized)
            # Different texts from a shared family violate the grouping contract.
            (root / "validation.csv").write_text("text,label,template_id\nsecond variant,1,shared\n")
            self.assertEqual(run_audit(root, manifest)["comparisons"][0]["interpretation"],
                             "GROUP_BOUNDARY_VIOLATION")
            # The same input reuse outside an evaluation boundary is not called leakage.
            config = json.loads(manifest.read_text())
            config["boundaries"] = []
            manifest.write_text(json.dumps(config))
            self.assertEqual(run_audit(root, manifest)["comparisons"][0]["interpretation"],
                             "INVENTORY_REUSE_NOT_AUTOMATIC_LEAKAGE")
            config["datasets"][1]["path"] = "missing.csv"
            manifest.write_text(json.dumps(config))
            self.assertEqual(run_audit(root, manifest)["missing_inputs"], ["validation"])

    def test_union_preserves_group_namespaces_and_row_references(self):
        a = rows({"text": "a", "label": "0", "template_id": "family"}, namespace="generator", dataset="train")
        union, _, _ = load_dataset(Path('.'), {"members": ["train"]}, {"train": a})
        b = rows({"text": "b", "label": "1", "template_id": "family"}, namespace="generator")
        self.assertEqual(union[0]["_ref"], "train:1")
        self.assertEqual(overlap(union, b)["groups"]["template_id"]["shared_groups"], 1)

    def test_cli_rejects_invalid_options_without_creating_output(self):
        result = subprocess.run([sys.executable, "-m", "src.dataset_audit", "--near-threshold", "nan"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
