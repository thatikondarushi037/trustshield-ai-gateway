# Holdout preparation and annotation (guideline annotation-1)

**NOT READY: no independent material has been collected.** Review this workflow
before collecting or freezing. It implements the independent-holdout protocol,
not a proof of independence. No old evaluation examples are transformed into new
holdout material.

## Practical gaps and safeguards

The earlier protocol lacked executable schemas, separate rater submissions,
adjudication transitions, disagreement summaries, stale-review detection,
connected-group checks, precollection plan binding and freeze verification.
These now have tooling. Real identity, licensing, blinding and semantic lineage
still require custodian evidence; checked booleans and new UUIDs are not proof.

## Workspace and formats

```powershell
.\.venv\Scripts\python.exe -m src.holdout_workflow init
.\.venv\Scripts\python.exe -m src.holdout_workflow validate
```

`init` creates empty forms and refuses an existing directory. `--format json`
selects JSON arrays rather than CSV. All raw material and future snapshots stay
under ignored `data/holdout/`; the CLI rejects collection paths elsewhere.
Git ignore is not encryption/access control: restrict OS file permissions to the
custodian and relevant annotators. Do not put real prompts, functional credentials
or real private values here. This version accepts FICTIONAL content only. No
licensed material has been obtained; a future licensed track requires permission,
privacy review and documented lineage for fictionalization. It must not launder
old repository evaluation examples into a purportedly independent source.

The [JSON Schema](../config/holdout_schema.json) comes from typed Pydantic models
in `src/holdout_schema.py`. Extra fields are forbidden. Exactly one CSV or JSON
file exists per table. CSV headers match all model fields, booleans are lowercase
true/false, nullable derivation parents are blank. JSON uses booleans/null.
Timestamps require UTC offsets. CLI errors never echo submitted values.

| Private file | Contents |
|---|---|
| collection.json | version, PREPARATION/COLLECTED_REVIEWED, custodian UUID, attestation |
| records.csv/json | record UUID, text, source UUID/revision/time, group namespace, template family, author/document/person groups, derivation parent, language/category, partition, FICTIONAL content kind |
| sources.json | source UUID/revision/origin, consent/license evidence path/hash, no-example/no-model-output exposure attestations, verifier UUID |
| annotations.csv/json | record/rater UUID, label, guideline version, blind-independence attestation, reason code, timestamp |
| adjudications.csv/json | record/adjudicator UUID, final label or EXCLUDE, guideline/reason, timestamp |
| leakage_reviews.csv/json | candidate UUID, known reference, content fingerprints, custodian UUID, disposition/reason |

Keep actual consent, collection and revision evidence at `evidence/<opaque-name>`;
paths cannot escape the workspace, and hashes must match. `planning.json` records
production model/code, rules, schema/guidelines and reference-manifest hashes
before collection. Changed plans block readiness. Do not edit hashes to conceal
post-collection changes; use a new reviewed plan and decide whether fresh material
is required. This is a hash binding, not authenticated pre-registration.

Group IDs represent actual shared lineage. Related variants share a family ID;
assigning a new ID cannot confer independence. Author/document/person IDs are
global opaque pseudonyms; family IDs are namespaced. When no entity is shared,
use distinct opaque groups, not a common NONE joining unrelated records.
Connected components include all these relations and derivation parents. A
component cannot cross DEVELOPMENT/HOLDOUT.

## Annotation and adjudication

After collection is approved, create each private assignment using the `package`
action with `--annotator-id <rater-UUID>`. It contains record IDs and texts only,
without source-derived target labels, predictions or other ratings. Distribute
packages separately. Annotators do not discuss votes or see model output before
submitting; tooling cannot authenticate people or prevent offline sharing.

Each rater returns a private JSON array matching Annotation. Import with `submit
--submission <private-relative-file.json>`. Each submission is one assigned rater;
duplicate votes are rejected instead of replacing history. Never edit votes to
remove disagreement. The CLI does not transmit packages or contact anyone.

Label independently from the frozen task definition, not source identity, model
output or regex detection:

- SAFE / CONCEPT_ONLY: discussion or generic instructions without an in-scope
  identifier, private value or credential disclosure.
- SENSITIVE / OBSERVED_DISCLOSURE: an in-text disclosure under the study
  definition. Fictional values represent disclosure; fictional does not mean SAFE.
- UNCERTAIN / AMBIGUOUS: insufficient context or an unresolved definition; do not
  force a binary label or copy a detector's result.
- OUT_OF_SCOPE / OUT_OF_SCOPE: unsupported language/target; adjudicate/exclude,
  never count it as a correct negative by default.

The planned withholding target includes privacy and credential disclosure;
preserve categories and distinguish privacy-detector from policy performance.
The privacy classifier alone is not the credential detector. REVIEW is abstention,
not confirmed disclosure. Freeze these semantics before later scoring.

Two distinct blind votes are required. Matching binary votes resolve directly.
Disagreement or matching UNCERTAIN/OUT_OF_SCOPE requires one third adjudicator,
distinct from both raters and the author identifier. Final outcomes are SAFE,
SENSITIVE or EXCLUDE. Guideline/reason versions and chronological timestamps are
checked. Supplemental adjudication cannot overwrite original votes. UUID equality
checks are not verification of physical identity; custody controls remain needed.

Reports preserve pre-adjudication agreement/disagreement counts/rates, exclusion
and resolution counts. Cohen's kappa is only reported for a fixed rater pair and
nondegenerate expected agreement; otherwise null. No universal agreement cutoff
is claimed. Closure plus custodian review is required; final consensus must not
hide high original disagreement.

## Leakage checks and readiness

Every manifest dataset is loaded. AST extraction additionally reads string
literals of at least 20 characters in source/tests without execution. This is
conservative and includes some prose/code constants. Missing registered inputs,
unreadable source or unregistered raw/processed CSVs block readiness. Missing
historical document/person IDs prevent complete historical group proof.

Known exact/normalized reuse, collection duplicates/conflicting labels, historical
same-scope family/group overlap, and cross-partition connected groups block
readiness. No automatic relabeling, rewriting, deletion or split repair occurs.
Quarantine confirmed reuse and linked components privately with an audit trail;
simply assigning EXCLUDE does not make copied material independent.

Near screening uses character 3-5-gram TF-IDF cosine >=0.85, with sparse 32-query
blocks and all qualifying pairs rather than truncated top-k. This fits an audit
representation, not a classifier. Worst-case computation is quadratic; it is not
an unbounded large-data retrieval guarantee. Exact matches are checked separately.
`validate` writes all review jobs privately to `leakage_jobs.json`, containing IDs,
references and fingerprints, not copied text. Duplicate historical copies use one
canonical reference. Review texts locally. Only a custodian BENIGN decision with
DISTINCT_INTENT/GENERIC_WORDING and current fingerprints clears a candidate.
RELATED/UNRESOLVED, duplicate or stale reviews block. Exact/group overlap cannot
be overridden by a near-review decision. Similarity is not proof of copying, and
a benign attestation is not proof of independence.

Versioned `config/holdout_rules.json` requires 300 resolved rows and 30 connected
components per class, two source tracks with both labels in each, and both labels
in each required category. These are planning floors, not power guarantees. Unit
tests lower floors only in temporary fixtures. Do not lower real rules to make an
incomplete collection pass.

Blockers yield NOT_READY and exit 2. Passing means READY_FOR_CUSTODIAN_REVIEW,
never proven independence. Public `reports/holdout_preparation.json` contains
counts and fixed issue codes, not raw text, per-text hashes, individual ratings,
annotator identities, evidence values or exception messages.

## Future freeze, not performed in this milestone

After explicit review, actual collection and clearance, the custodian may invoke
`freeze` with a fresh `--version` and `--confirm-freeze`. It revalidates the plan,
collection and current threshold, snapshots private inputs/evidence and resolved
`dataset.csv` under `frozen/<version>`, and never overwrites an existing version.
Staging is published only after all hashes are checked; failed staging is removed.
The private manifest binds dataset/input/annotation/evidence hashes, versions,
reference inventory, production/workflow code, model bytes and evaluation rules.
The model is never deserialized, trained or replaced. No scoring is performed.

The future `verify --version <version>` checks for changed/missing/extra snapshot
files. It does not authenticate a maliciously replaced manifest or enforce OS
immutability. Keep trusted manifest copies and restricted permissions; record
access externally. Any inspection-driven model changes retire that holdout to
development and require fresh evaluation material.

## Operational limits

Import submissions serially through a single custodian process. This is an offline
file workflow, not a concurrent multi-writer annotation service. Assignment files
must be distributed separately; file schemas cannot enforce actual human blinding.

Near checks also screen distinct connected components inside the candidate
collection, including development/holdout pairs. Same-component variants within
one partition are counted through group-level sampling instead of automatically
being called leakage. Historical author/document/person IDs are checked when
available; their missing coverage is reported explicitly.

Plan and freeze hashes identify the saved artifact, not the API's in-memory
parameters: FastAPI currently fits at startup. This workflow does not start or
import that API, and it does not establish live model identity.
