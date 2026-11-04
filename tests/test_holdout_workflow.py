import csv
import json
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from src.holdout_schema import Bundle
from src.holdout_workflow import (
    EVALUATION_FILES, annotation_package, fingerprint, freeze, initialize,
    inspect_collection, read_bundle, sha, submit_annotations, verify_snapshot,
)


def uid(number):
    return str(UUID(int=number))


class TestHoldoutWorkflow(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for name in EVALUATION_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fixture evaluation file\n")
        (self.root / "src/privacy_decision_engine.py").write_text("SAFE_THRESHOLD = 0.5\n")
        self.rules = {"version": "test-1", "guideline_version": "annotation-1",
                      "minimum_rows_per_class": 1, "minimum_components_per_class": 1,
                      "minimum_sources": 1, "required_categories": ["EMAIL"],
                      "near_threshold": 0.85, "evaluation": {"decision_threshold": 0.5}}
        (self.root / "config/holdout_rules.json").write_text(json.dumps(self.rules))
        path = self.root / "data/processed/known.csv"
        path.parent.mkdir(parents=True)
        path.write_text("text,label,template_id\nMarine biodiversity survey methods in remote ocean habitats.,0,old_family\n")
        (self.root / "config/dataset_audit.json").write_text(json.dumps({"datasets": [
            {"id": "known", "path": "data/processed/known.csv", "group_namespace": "old"}]}))
        self.directory = self.root / "data/holdout/candidate"
        initialize(self.directory, "json", self.root)

    def write(self, name, value):
        (self.directory / f"{name}.json").write_text(json.dumps(value))

    def read(self, name):
        return json.loads((self.directory / f"{name}.json").read_text())

    def valid_fixture(self):
        (self.directory / "evidence/consent.txt").write_text("fictional test evidence, not real independence")
        self.write("collection", {"version": "fixture-1", "state": "COLLECTED_REVIEWED",
                                  "custodian_id": uid(204), "independence_attested": True})
        self.write("sources", [{"source_id": uid(100), "revision": "revision-1",
                                "origin_kind": "INDEPENDENT_AUTHOR", "evidence_file": "evidence/consent.txt",
                                "evidence_sha256": sha(self.directory / "evidence/consent.txt"),
                                "license_or_consent_verified": True, "independence_attested": True,
                                "repository_examples_exposure": "NONE", "model_outputs_exposure": "NONE",
                                "verified_by": uid(204)}])
        records = []
        for number, text in ((1, "Explain ordinary lunar weather patterns for fictional travelers."),
                             (2, "My email is holdout-fixture@example.com.")):
            records.append({"record_id": uid(number), "text": text, "source_id": uid(100),
                            "source_revision": "revision-1", "collected_at": "2026-01-01T00:00:00Z",
                            "group_namespace": "new_source", "template_family_id": f"family_{number}",
                            "author_group_id": uid(10 + number), "document_group_id": uid(20 + number),
                            "person_group_id": uid(30 + number), "derivation_parent_id": None,
                            "language": "en", "category": "EMAIL", "partition": "HOLDOUT", "content_kind": "FICTIONAL"})
        self.write("records", records)
        annotations = []
        for number, label in ((1, "SAFE"), (2, "SENSITIVE")):
            for annotator in (201, 202):
                annotations.append({"record_id": uid(number), "annotator_id": uid(annotator), "label": label,
                                    "guideline_version": "annotation-1", "independent_blind": True,
                                    "reason_code": "CONCEPT_ONLY" if label == "SAFE" else "OBSERVED_DISCLOSURE",
                                    "annotated_at": "2026-01-02T00:00:00Z"})
        self.write("annotations", annotations)
        return records

    def result(self):
        return inspect_collection(self.root, self.directory)

    def test_empty_preparation_is_not_ready_and_not_frozen(self):
        report, _ = self.result()
        self.assertEqual(report["status"], "NOT_READY")
        self.assertIn("NO_INDEPENDENT_MATERIAL_COLLECTED", report["blocking_findings"])
        self.assertFalse((self.directory / "frozen").exists())

    def test_valid_fixture_passes_mechanical_gates_only(self):
        self.valid_fixture()
        report, _ = self.result()
        self.assertEqual(report["status"], "READY_FOR_CUSTODIAN_REVIEW", report["blocking_findings"])
        self.assertEqual(report["class_counts"], {"SAFE": 1, "SENSITIVE": 1})
        self.assertEqual(report["annotation_summary"]["agreement_rate"], 1)

    def test_missing_fields_and_private_extra_fields_are_sanitized(self):
        self.write("records", [{"text": "fictional-private-secret", "unknown": "private-extra-value"}])
        report, _ = self.result()
        self.assertIn("INVALID_ROW_RECORDS", report["blocking_findings"])
        self.assertNotIn("fictional-private-secret", json.dumps(report))
        self.assertNotIn("private-extra-value", json.dumps(report))

    def test_two_distinct_blind_annotators_required(self):
        self.valid_fixture()
        rows = self.read("annotations")
        rows[1]["annotator_id"] = rows[0]["annotator_id"]
        self.write("annotations", rows)
        self.assertIn("TWO_DISTINCT_ANNOTATORS_REQUIRED", self.result()[0]["blocking_findings"])
        rows[1]["independent_blind"] = False
        self.write("annotations", rows)
        self.assertIn("INVALID_ROW_ANNOTATIONS", self.result()[0]["blocking_findings"])

    def test_disagreement_requires_independent_adjudication(self):
        self.valid_fixture()
        rows = self.read("annotations")
        rows[1].update(label="SENSITIVE", reason_code="OBSERVED_DISCLOSURE")
        self.write("annotations", rows)
        report, _ = self.result()
        self.assertEqual(report["annotation_summary"]["disagreements"], 1)
        self.assertEqual(report["annotation_summary"]["disagreement_rate"], 0.5)
        self.assertIn("ADJUDICATION_REQUIRED_OR_DUPLICATED", report["blocking_findings"])
        decision = {"record_id": uid(1), "adjudicator_id": uid(201), "final_label": "SAFE",
                    "guideline_version": "annotation-1", "reason_code": "LABEL_RESOLVED",
                    "adjudicated_at": "2026-01-03T00:00:00Z"}
        self.write("adjudications", [decision])
        self.assertIn("INVALID_ADJUDICATION_CONTEXT", self.result()[0]["blocking_findings"])
        decision["adjudicator_id"] = uid(203)
        self.write("adjudications", [decision])
        self.assertEqual(self.result()[0]["status"], "READY_FOR_CUSTODIAN_REVIEW")

    def test_uncertain_agreement_still_requires_adjudication(self):
        self.valid_fixture()
        rows = self.read("annotations")
        for row in rows[:2]:
            row.update(label="UNCERTAIN", reason_code="AMBIGUOUS")
        self.write("annotations", rows)
        self.assertIn("ADJUDICATION_REQUIRED_OR_DUPLICATED", self.result()[0]["blocking_findings"])

    def test_exact_known_reuse_and_label_conflict_block(self):
        records = self.valid_fixture()
        records[1]["text"] = "Marine biodiversity survey methods in remote ocean habitats."
        self.write("records", records)
        findings = self.result()[0]["blocking_findings"]
        self.assertIn("EXACT_KNOWN_REUSE", findings)
        self.assertIn("KNOWN_LABEL_CONFLICT", findings)

    def test_normalized_reuse_blocks(self):
        records = self.valid_fixture()
        records[0]["text"] = "  MARINE biodiversity survey methods in remote ocean habitats.  "
        self.write("records", records)
        self.assertIn("NORMALIZED_KNOWN_REUSE", self.result()[0]["blocking_findings"])

    def test_known_template_group_blocks_without_text_overlap(self):
        records = self.valid_fixture()
        records[0].update(group_namespace="old", template_family_id="old_family")
        self.write("records", records)
        self.assertIn("KNOWN_TEMPLATE_OR_SOURCE_GROUP_OVERLAP", self.result()[0]["blocking_findings"])

    def test_transitive_group_separation_spans_namespaces(self):
        records = self.valid_fixture()
        records[0]["partition"] = "DEVELOPMENT"
        records[1].update(group_namespace="different", author_group_id=records[0]["author_group_id"])
        self.write("records", records)
        self.assertIn("CROSS_PARTITION_CONNECTED_GROUP", self.result()[0]["blocking_findings"])

    def test_collection_duplicates_and_label_conflicts(self):
        records = self.valid_fixture()
        records[1]["text"] = records[0]["text"]
        self.write("records", records)
        report, _ = self.result()
        self.assertIn("DUPLICATE_COLLECTION_TEXT", report["blocking_findings"])
        self.assertIn("COLLECTION_LABEL_CONFLICT", report["blocking_findings"])

    def test_near_review_is_complete_and_bound_to_current_content(self):
        records = self.valid_fixture()
        records[0]["text"] = "Marine biodiversity survey methods in remote ocean habitats!"
        self.write("records", records)
        report, state = self.result()
        self.assertEqual(report["near_candidate_pairs"], 1)
        self.assertIn("UNRESOLVED_NEAR_DUPLICATE", report["blocking_findings"])
        job = state["near_jobs"][0]
        self.write("leakage_reviews", [dict(job, reviewer_id=uid(204), disposition="BENIGN", reason_code="DISTINCT_INTENT")])
        self.assertEqual(self.result()[0]["status"], "READY_FOR_CUSTODIAN_REVIEW")
        records[0]["text"] = records[0]["text"].replace("!", "?")
        self.write("records", records)
        self.assertIn("UNRESOLVED_NEAR_DUPLICATE", self.result()[0]["blocking_findings"])

    def test_missing_reference_and_extra_unregistered_csv_block(self):
        self.valid_fixture()
        path = self.root / "data/processed/unregistered.csv"
        path.write_text("text,label\nfictional unregistered source,0\n")
        self.assertIn("MISSING_OR_UNREGISTERED_REFERENCE", self.result()[0]["blocking_findings"])

    def test_missing_registered_reference_blocks(self):
        self.valid_fixture()
        (self.root / "data/processed/known.csv").unlink()
        self.assertIn("MISSING_OR_UNREGISTERED_REFERENCE", self.result()[0]["blocking_findings"])

    def test_near_matches_between_candidate_components_block(self):
        records = self.valid_fixture()
        records[1]["text"] = records[0]["text"][:-1] + "!"
        self.write("records", records)
        report, _ = self.result()
        self.assertEqual(report["within_collection_near_pairs"], 1)
        self.assertIn("UNRESOLVED_NEAR_DUPLICATE", report["blocking_findings"])

    def test_timestamps_are_compared_as_instants_not_strings(self):
        records = self.valid_fixture()
        records[0]["collected_at"] = "2026-01-01T00:00:00+10:00"
        self.write("records", records)
        ratings = self.read("annotations")
        for rating in ratings[:2]:
            rating["annotated_at"] = "2025-12-31T20:00:00Z"
        self.write("annotations", ratings)
        self.assertEqual(self.result()[0]["status"], "READY_FOR_CUSTODIAN_REVIEW")

    def test_cyclic_derivation_is_invalid_provenance(self):
        records = self.valid_fixture()
        records[0]["derivation_parent_id"] = records[1]["record_id"]
        records[1]["derivation_parent_id"] = records[0]["record_id"]
        self.write("records", records)
        self.assertIn("CYCLIC_DERIVATION_LINEAGE", self.result()[0]["blocking_findings"])

    def test_provenance_evidence_and_plan_changes_block(self):
        self.valid_fixture()
        (self.directory / "evidence/consent.txt").write_text("changed evidence")
        self.assertIn("MISSING_OR_CHANGED_PROVENANCE_EVIDENCE", self.result()[0]["blocking_findings"])
        (self.root / "models/privacy_model_v02.joblib").write_text("changed model fixture")
        self.assertIn("PRECOLLECTION_EVALUATION_PLAN_CHANGED", self.result()[0]["blocking_findings"])

    def test_sample_floor_blocks_small_collection(self):
        self.valid_fixture()
        self.rules["minimum_rows_per_class"] = 300
        (self.root / "config/holdout_rules.json").write_text(json.dumps(self.rules))
        self.assertIn("CLASS_SAMPLE_FLOOR_NOT_MET", self.result()[0]["blocking_findings"])

    def test_annotation_package_hides_other_labels_and_cannot_overwrite(self):
        self.valid_fixture()
        self.assertEqual(annotation_package(self.directory, uid(201)), 2)
        jobs = json.loads((self.directory / f"annotation_jobs/{uid(201)}.json").read_text())
        self.assertEqual(set(jobs[0]), {"record_id", "text"})
        with self.assertRaises(FileExistsError):
            annotation_package(self.directory, uid(201))

    def test_independent_submission_rejects_duplicates(self):
        self.valid_fixture()
        original = self.read("annotations")
        self.write("annotations", [])
        annotation_package(self.directory, uid(201))
        path = self.directory / "submission.json"
        path.write_text(json.dumps([r for r in original if r["annotator_id"] == uid(201)]))
        self.assertEqual(submit_annotations(self.directory, path), 2)
        with self.assertRaises(ValueError):
            submit_annotations(self.directory, path)

    def test_csv_and_json_parity(self):
        self.valid_fixture()
        first, _ = self.result()
        for table in ("records", "annotations", "adjudications", "leakage_reviews"):
            path = self.directory / f"{table}.json"
            rows = json.loads(path.read_text())
            from src.holdout_schema import TABLES
            with path.with_suffix(".csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=TABLES[table].model_fields)
                writer.writeheader()
                for row in rows:
                    if "independent_blind" in row:
                        row["independent_blind"] = "true"
                    writer.writerow(row)
            path.unlink()
        self.assertEqual(first, self.result()[0])

    def test_schema_has_no_raw_example_values(self):
        schema = Bundle.model_json_schema()
        self.assertIn("Record", schema["$defs"])
        self.assertNotIn("holdout-fixture@example.com", json.dumps(schema))

    def test_freeze_requires_ready_collection_and_confirmation(self):
        with self.assertRaises(ValueError):
            freeze(self.root, self.directory, "v1", True)
        self.valid_fixture()
        with self.assertRaises(ValueError):
            freeze(self.root, self.directory, "v1")
        self.assertFalse((self.directory / "frozen").exists())

    def test_freeze_hashes_rules_inputs_and_detects_tampering(self):
        records = self.valid_fixture()
        report, _ = self.result()
        self.assertEqual(report, self.result()[0])
        self.assertNotIn(records[1]["text"], json.dumps(report))
        frozen = freeze(self.root, self.directory, "fixture-v1", True)
        self.assertTrue(verify_snapshot(frozen))
        manifest = json.loads((frozen / "manifest.json").read_text())
        self.assertIn("models/privacy_model_v02.joblib", manifest["implementation"])
        self.assertEqual(manifest["evaluation_rules"], self.rules)
        with self.assertRaises(ValueError):
            freeze(self.root, self.directory, "fixture-v1", True)
        (frozen / "dataset.csv").write_text("tampered fixture")
        self.assertFalse(verify_snapshot(frozen))

    def test_freeze_verification_rejects_unlisted_files(self):
        self.valid_fixture()
        frozen = freeze(self.root, self.directory, "fixture-extra", True)
        (frozen / "unexpected.txt").write_text("unlisted fixture")
        self.assertFalse(verify_snapshot(frozen))


if __name__ == "__main__":
    unittest.main()
