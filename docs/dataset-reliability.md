# Dataset reliability and generalization workflow

Run from the repository root against the already running local API:

```powershell
.\.venv\Scripts\python.exe -m src.dataset_reliability --live-api http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_dataset_reliability.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_dataset_audit.py -v
git diff --check
```

Omit `--live-api` for an offline artifact-only report. No API is started. Never
import `src.api` for evaluation: it calls `train_model()` at import time. Unlike
the old scripts, this workflow never calls fit, dumps a model, executes embedded
evaluation scripts, or alters data. Only the existing trusted local
`models/privacy_model_v02.joblib` is loaded, using the same `analyze_message`
implementation and threshold used by the gateway. Do not load untrusted joblib
artifacts because deserialization can execute code.

Reports are `reports/dataset_reliability.json` and `.md`. They record model,
input, tool, manifest and production-analysis source fingerprints, aggregate
metrics, limited error row references, source cross-tabs and local lexical pair
review. No raw text, sensitive values, exception messages or individual scores
are exported. Before writing, the command checks every loaded record's full text
against report string fields and Markdown, failing without echoing content on a
match. Its privacy-check counts are included in the command output. This is a
full-text guard, not a generic detector of every possible sensitive substring;
the aggregate-only report structure is the primary minimization control.
Same input/environment/service responses yield the same output.
The live check sends existing evaluation text only to loopback `/analyze`, not
to a backend or `/gateway`; it does not create review/audit records. A failed or
mismatching requested live check returns exit code 2 and is explicitly reported.

The saved artifact lacks a training manifest. It cannot automatically be called
the identical model currently held in the API's memory: the API fits at startup.
Live comparison checks hybrid decisions, rounded ML scores and detection types
on the evaluated rows. Agreement supports bounded consistency of measured hybrid
behavior, not parameter identity, unrounded score equality, or artifact provenance.
ML-only metrics refer specifically to the frozen artifact; the live endpoint
does not expose its binary estimator's predict output. No classifier is retrained
to reconcile differences.

The seven evaluation inputs are legacy validation/test, synthetic validation,
independent evaluation, challenge CSV, embedded model challenge, and embedded
frozen evaluation. The repeated comparison-script challenge list is not counted
again. No pooled score is reported, and every input has an independence warning.
Training/parent corpora are inspected for source distribution, not presented as
held-out performance. A zero text overlap does not establish independent authorship.

Binary matrix order is [[TN, FP], [FN, TP]], positive label SENSITIVE=1.
Precision=TP/(TP+FP), recall=TP/(TP+FN), F1=2TP/(2TP+FP+FN),
FPR=FP/(FP+TN), FNR=FN/(FN+TP). Undefined denominators are null rather than zero.
Two views are retained: the artifact's binary ML prediction and hybrid non-SAFE
(REVIEW or SENSITIVE). For the latter, FNR is the fraction of sensitive requests
classified SAFE, while FPR includes SAFE requests held for review. REVIEW does
not establish a disclosure or become a confirmed true positive. The separate
2x3 SAFE/REVIEW/SENSITIVE matrices and review counts preserve this distinction.
This is detector evaluation; secret-first gateway policy, redaction quality,
backend generation and HTTP error behavior are outside these metrics.

Pair reviews are reproducible lexical triage rather than an expert semantic
oracle. The two raw pairs are compared only in memory. Negation/content edits
remain inconclusive; near-identical function-word/punctuation edits are likely
duplicates, not proof of common origin. No raw edit fragments are serialized.
Reviewing these legacy rows further exposes them to development; do not reuse
their scores as fresh independent evidence. See the report for current findings.

The legacy builder declares one upstream collection per label. Observed CSVs
retain no source field for legacy rows. Inferred origin-by-label is therefore
kept separate from observed source counts: without original IDs/revisions and
within-source labels, causal source dependence cannot be estimated or separated
from real privacy signal. Label 1 is assigned to English source_text without
checking the mask on every row. The combined corpus's balanced coarse source
labels do not repair that underlying confounding.

Follow [the independent holdout protocol](independent-holdout.md) for the next
collection. No independently sourced holdout exists as a result of this command.
