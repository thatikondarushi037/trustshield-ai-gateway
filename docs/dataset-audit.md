# ML-1: dataset quality, provenance, and leakage auditing

This workflow audits the local dataset snapshot without training a classifier,
loading a saved model, executing a generator, contacting a remote dataset service,
or changing the gateway. It uses the existing scikit-learn dependency only for
lexical similarity. The manifest makes dataset roles and comparisons reviewable.

## Reproduce

From the repository root, using the installed project dependencies:

```powershell
.\.venv\Scripts\python.exe -m src.dataset_audit
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

Inputs must already exist locally. The installation instructions in README create
the synthetic training/validation and hard-example files; the audit does not
recreate or download missing historical corpora. Missing inputs are listed and
cause CLI exit code 2. Exit code 0 means analysis completed, not that data is clean.
Quality findings are reported, never automatically removed or relabeled.

The default outputs are `reports/ml1_dataset_audit.json` and `.md`. The JSON includes
input file SHA-256 checksums, source-script checksums, manifest/tool checksums,
Python/scikit-learn/SciPy versions, parameters, schemas, class/source cross-tabs,
missing metadata, duplicate/conflict counts, overlap counts and candidate row
references. There are deliberately no timestamps or host paths. Identical inputs,
configuration, tool and numerical environment produce identical output bytes.
File checksums establish snapshot identity, not proof of source authenticity.

References such as `legacy_train:451` mean the 451st data record, excluding the CSV
header (not necessarily a physical line for multiline CSV fields). Embedded
examples use their 1-based literal-list position. The active-training union keeps
the original component references and namespaces. Inspect those rows locally;
never paste private texts into a public issue or generated report.

## Interpretation

- **Exact** means identical nonblank text. Duplicate counts distinguish groups
  from excess rows. Conflicts require both valid labels 0 and 1 for the same text.
- **Normalized** applies NFKC Unicode normalization, case folding and whitespace
  collapse. It retains punctuation and identifier values. Normalized reuse is a
  separate review finding rather than silently redefining exact duplication.
- All dataset pairs receive exact/normalized checks. Only manifest `boundaries`
  are intended evaluation separations. Parent/subset overlap and the same
  challenge list stored in two scripts are expected inventory reuse.
- Same-scope template/pair/group/source-group IDs are compared without exposing
  their values. A shared group at an evaluation boundary violates that grouping
  contract, even when its texts differ. IDs from unrelated generators are not
  comparable. A zero overlap with partial coverage is not a complete guarantee.
- `source` is a collection name, not a document/person ID. Shared collections do
  not automatically establish leakage. No actual input retains `source_group`
  or upstream document/person IDs, so that separation cannot be verified.
- Similarity does not establish common ancestry, equivalent labels or copying.
  Leakage also includes evaluation-driven tuning that text matching cannot prove.

## Near-duplicate method and scaling

The default screen uses character-within-word TF-IDF 3-5 grams and L2 cosine
similarity **>= 0.90**, after the documented normalization. IDF is fit separately
on each comparison's sorted unique texts. This is an audit representation, not
classifier training; its scores are neither probabilities nor calibrated risks.
Scores may change with the comparison corpus, so do not compare them as universal
distances. Character grams tolerate small edits and identifier substitutions,
but do not reliably detect semantic paraphrases or derivation from feedback.
The representation is bag-like: word reordering can even yield cosine 1 for
different texts. Therefore candidates remain suspicious, not definite leakage.

Exact/normalized matches are excluded from near counts. The report counts unique
text pairs, corresponding row-pair multiplicities and opposite-label candidates.
Only the best 10 references/scores are retained; **counts are not truncated**.
Within-file comparisons remove symmetric/self pairs. Near analysis covers every
input internally plus explicit `near_comparisons`, not every cross-file pair.

Normalized texts are deduplicated before vectorization. Sparse products are
computed in 64-query blocks, never as a complete dense N-by-N matrix. Peak
similarity storage is bounded by a block times the reference count, plus the
sparse feature matrices; worst-case computation is still quadratic. Lower
`--batch-size` for memory pressure. This is practical for the local 6,000-row
corpus, not an unbounded large-data guarantee. For millions of rows, first add
validated MinHash/ANN candidate retrieval and measure its recall against small
exhaustive fixtures; approximate retrieval is not silently used here.

For a more permissive manual-review screen, without changing the classifier:

```powershell
.\.venv\Scripts\python.exe -m src.dataset_audit --near-threshold 0.80 --batch-size 32 --output reports/ml1_review_080
```

Expect more false positives at lower thresholds. Identifier masking and semantic
embeddings are not part of this milestone. Short texts and meaning-changing
edits need particular care. A zero candidate count is not proof of independence.

## Provenance evidence and actionable findings

The manifest inventories 13 CSVs, three embedded challenge/frozen lists, and one
virtual current-training union. Label 0 means SAFE and label 1 SENSITIVE. Raw
datasets and model artifacts remain ignored; only metadata reports are shareable.

1. `src/build_dataset.py` assigns label 0 to filtered `mteb/banking77` samples
   and label 1 to English `ai4privacy/pii-masking-micro-100k` source texts. These
   are **code-declared origins**, not row-level verified provenance. The positive
   selection does not check each record's privacy mask. Dataset revisions,
   original row IDs, acquisition dates and licensing evidence are not retained.
   Source and label are confounded by construction; a model can learn style or
   length rather than privacy. Recover manifests and validate labels before
   interpreting generalization claims. No remote provenance was verified here.
2. The 780-row length-matched corpus discards source IDs; `create_splits.py`
   performs a stratified random split (546/117/117). Exact separation is intact,
   but the default audit finds one train/validation and one train/test near pair
   (cosines approximately 0.9153 and 0.9770). Investigate those row references
   before reusing legacy held-out metrics; shared wording alone is not proof.
3. The 40-row synthetic generator has 20 template families. Its 30/10 split
   separates 15/5 families, with no shared text, pair IDs or template IDs.
   This is better than a row split, but only five held-out families is weak
   evidence, and related wording or authorship can still cross family boundaries.
4. The current classifier concatenates the 30 synthetic-training and 30 hard
   rows (60 total, balanced 30/30), not the legacy corpus or its random split.
   Its checked evaluation boundaries have zero exact/normalized matches and
   zero near candidates at 0.90. The hard set has five category-level `group_id`
   values; it has no per-template or upstream document lineage. The independent
   evaluation has 40 balanced examples, but no comparable template-group IDs.
5. `build_v02_hard_examples.py` contains hand-authored literals and reads no
   challenge/evaluation dataset. The audit verifies that its literal text/label
   multiset matches the current CSV. No exact reuse was found against the
   independent evaluation, challenge CSV, embedded 20-row challenge, or frozen
   evaluation. However, `compare_v02_hard_examples.py` explicitly reuses the
   previous challenge list to assess improvement after adding hard examples.
   All these scripts first appear together in commit `227d5f8`; Git cannot
   establish their internal creation order or whether the author manually
   paraphrased evaluation failures. **Derivation remains unknown**. Absence of
   exact or high-cosine overlap does not establish an untouched test set.
6. The independent evaluation is read by `analyze_decision_thresholds.py` and
   rule-coverage/development scripts. Treat inspected results as development
   evidence. Reserve a new, versioned, genuinely untouched evaluation set before
   future model/threshold selection. This audit does not change any threshold.
7. The default snapshot has no within-input exact duplicates or label conflicts.
   Global duplication is expected because parent datasets, derived subsets and
   repeated challenge lists coexist. Do not sum their rows as independent data.
   The legacy 6,000-row corpus has 302 within-file near candidates at 0.90; review
   clusters and restore real source groups before creating new splits.

The concrete snapshot counts and checksums live in the generated reports. These
notes describe the inspected local snapshot and should be revised if its inputs
or builders change. No data was deleted, reassigned, regenerated or trained by
the audit. Existing regression tests independently train temporary in-memory
models and test persistence in temporary directories; they do not replace the
production model artifact.
