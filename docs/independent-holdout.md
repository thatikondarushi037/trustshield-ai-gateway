# Independent holdout protocol (proposed, not yet collected)

This protocol creates a future evaluation resource. No examples are generated or
collected by the reliability workflow. Existing challenge, frozen-evaluation,
independent-evaluation and audit-reviewed examples are development data. Do not
rewrite, translate, replace identifier values in, paraphrase, or prompt an LLM
with those examples to claim a new independent holdout.

## Freeze the question before collection

Freeze the artifact hash, production rule/code hashes, positive-label definition,
current 0.50 threshold, and planned metrics before any collection or scoring.
Separate two claims: detecting privacy-relevant content, and withholding content
from backend execution. REVIEW is abstention; it is not confirmed sensitive
content. Do not tune a threshold or fix rules using the holdout and then quote
the same set as an untouched test.

The initial target is English local-gateway requests spanning the five existing
PII categories, credential disclosure, mixed disclosures, and SAFE discussion of
privacy concepts. Keep out-of-scope disclosures and ambiguous cases as separate
strata. Do not infer labels from publisher/source or detector output.

## Collection and provenance

Use independently recruited authors who have not seen repository examples or
model outputs. Give only the frozen task/label specification, not old examples
or template families. Each author writes both classes using entirely fictional
identifiers and nonfunctional credential placeholders. A second collection track
may use an independently acquired, licensed corpus with explicit permission and
offline privacy review; no source has been acquired or approved by this protocol.
Public availability alone is not license or independence evidence. Do not fetch
real user prompts or live credentials merely to make evaluation realistic.

For each private record retain: random record ID; immutable collection/revision
ID; origin and license/consent evidence; acquisition date; author/document/person
group (pseudonymous); original template/semantic-family ID; any derivation parent;
language; category; label; annotation version; two annotator IDs and adjudication
status. Keep raw text and detailed provenance in access-controlled ignored storage,
not Git. Maintain hashes of the frozen files for local verification. Reports
contain counts, aggregate metrics, and a small number of opaque row IDs only.

## Labeling and isolation

Two annotators label independently while blind to predictions, using a written
privacy definition. Resolve disagreements through adjudication; report disagreement
and exclusion counts. Do not automatically label every source row positive or
use regex detection as ground truth. Both labels must occur within each source
track and across authors wherever feasible, reducing source/label confounding.

Build connected components over shared author, document/person, collection
derivation and template/semantic-family relationships. Assign complete components
to development or holdout before use, never rows independently. Related SAFE and
SENSITIVE variants remain in one component. Reserve whole source tracks for a
separate cross-source generalization assessment when sufficient sources exist.
Template separation alone cannot compensate for shared authors or source style.

An independent custodian screens candidate holdout against **all** historical
training, development, challenge and evaluation texts, including literals in code.
Run exact, normalized and near-duplicate checks locally; review candidate
relationships and negation changes. Treat unknown lineage conservatively.
Quarantine confirmed reuse and linked components, record aggregate exclusions,
and do not disclose holdout examples to model developers. Similarity screening
is a necessary check, not a guarantee of semantic independence.

## Size, custody, scoring and retirement

Plan enough independent groups per source/category to support uncertainty
estimation. As an initial floor, aim for at least 300 SENSITIVE and 300 SAFE rows,
distributed across at least 30 isolated groups per class and multiple independent
source tracks; this is a planning target, not a guarantee of statistical power.
If observations were independent, zero misses in 300 positives would still give
an approximate 95% upper miss-rate bound of 1%; group correlation weakens that
claim. Pre-register grouped confidence intervals and report both group and row
counts. Do not pool repeated templates as independent trials.

Custodian freezes versioned data/provenance manifests and checksums, runs the
already-frozen model once, and publishes per-source/per-category confusion
matrices, precision, recall, F1, FPR/FNR, REVIEW counts, and false-SAFE rates.
Undefined denominators remain null. Retain a record of every access and model
version evaluated. Any inspection-driven model change retires the touched set
to development; collect a new independent test rather than repeatedly tuning
against this one. This milestone does not execute collection or model selection.

The executable schema, annotation guidelines, readiness gates and future freeze
procedure are documented in [holdout preparation](holdout-annotation.md).
Implementing the workflow does not collect or freeze an independent holdout.
