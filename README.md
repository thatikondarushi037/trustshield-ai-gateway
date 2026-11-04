## TrustShield AI Gateway — Infrastructure Checkpoint

TrustShield AI Gateway is a privacy-focused ML engineering project designed to identify potentially sensitive information before prompts are forwarded to AI models.

### Current capabilities

- TF-IDF + Logistic Regression text classification.
- Regex-based detection for email addresses, PINs, account numbers, phone numbers, and street addresses.
- Hybrid decision engine with three outcomes:
  - **SAFE:** Eligible for forwarding.
  - **SENSITIVE:** Explicit sensitive information detected; block or redact according to policy.
  - **REVIEW:** Potential sensitive information detected; hold for further review.
- Saved ML pipeline using `joblib`.
- Automated regression and model-persistence tests.
- Evaluation reports without raw message text.
- FastAPI analysis, redaction, demo gateway, and Ollama gateway endpoints.
- Secret-first ALLOW / BLOCK / HOLD policy enforcement.
- Local HOLD review queue with reject/rewrite actions; no approval bypass.
- Streamlit dashboard and authenticated persistent SQLite monitoring.
- Windows DPAPI-encrypted local monitoring-token configuration.

### Installation and synthetic training data

Tested on Windows with CPython 3.14 and Windows PowerShell 5.1. Install Python,
Git, and (for local AI generation) Ollama before starting. From a fresh clone:

```powershell
git clone --branch feature/v0.3-fastapi-gateway https://github.com/thatikondarushi037/trustshield-ai-gateway.git
cd trustshield-ai-gateway
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/split_v02_synthetic.py
.\.venv\Scripts\python.exe src/build_v02_hard_examples.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`requirements.txt` pins the tested direct dependency versions; it is not a full
transitive lockfile. The two builders use fictional values already in source and
create `data/processed/v02_synthetic_train.csv`,
`v02_synthetic_validation.csv`, and `v02_hard_examples.csv`. Run them before
tests or API startup. They require no private dataset or saved model artifact.
They overwrite those generated CSVs, so preserve any local experiments first.
The API trains its small privacy model on startup. Generated datasets, model
artifacts, runtime databases, logs, and local token files stay outside Git.

For Ollama generation, provision the model explicitly (this downloads it):

```powershell
ollama pull llama3.2:1b
ollama list
```

Keep Ollama running locally on `127.0.0.1:11434` (run `ollama serve` in a separate
terminal only if the installed Ollama service is not already running). Continue
with the monitoring initialization and two service startup commands below.
Ollama is not required for automated regression tests or the demo `/gateway`.

### V0.2 evaluation

A frozen-model evaluation was performed using 20 synthetic examples: 10 SAFE and 10 SENSITIVE.

| Actual label | SAFE decision | REVIEW decision | SENSITIVE decision |
|---|---:|---:|---:|
| SAFE | 9 | 1 | 0 |
| SENSITIVE | 0 | 8 | 2 |

**Observed results:**
- Sensitive messages incorrectly marked SAFE: 0/10.
- Safe messages automatically allowed: 9/10 (90%).
- Sensitive messages explicitly classified SENSITIVE: 2/10.
- Automated tests: 8 passed.

These results are preliminary. The dataset is small and synthetic, and it does not establish real-world privacy guarantees. The ML scores have not been calibrated. REVIEW decisions are held rather than forwarded automatically.

### Persistent security audit logging

Both `POST /gateway` and `POST /gateway/local` commit a metadata-only policy
record to `data/audit.db` before any approved backend execution. Existing analysis,
redaction, health, and gateway endpoints remain available. `GET /audit?limit=50`
returns lifetime gateway counts and recent records (limit 1–200); the Streamlit
dashboard displays this persistent view alongside its session metrics. Monitoring
requires a loopback client and `Authorization: Bearer <token>` matching the
server's `TRUSTSHIELD_AUDIT_TOKEN`; without configuration it is disabled (503).
Missing/incorrect credentials return 401 and non-loopback peers return 403.
The dashboard reads the token from its server process environment, never from a
browser input, and sends it only to the fixed loopback API URL.

Records contain a random audit ID, UTC timestamps, policy decision, known PII and
secret category labels, and execution status. They contain no raw prompts,
credentials, responses, hashes, exception messages, or free-form reasons.
The gateway response includes `audit_id` after a successful initial write.
Finalization adds non-negative `latency_ms` measured with a monotonic clock from
gateway entry through outcome recording, plus `backend_attempted` and
`backend_succeeded` indicators. The measurement excludes the final write's own
commit time. Monitoring provides average measured latency and recorded attempt /
success counts. Pending and historical unmeasured values remain null; counts of
recorded attempts are therefore not a complete count when finalization fails.

An ALLOW record starts as `PENDING`, then becomes `SUCCEEDED` or `FAILED`.
BLOCK/HOLD records use `NOT_ALLOWED`; review-queue write failures use
`REVIEW_FAILED`. BLOCK/HOLD are finalized with zero backend attempts/successes;
backend exceptions finalize with attempted=1 and succeeded=0. Each record can be
finalized only once. Existing databases are migrated in place by adding nullable
columns; historical measurements are not fabricated. Counts of allowed requests describe policy decisions, not
successful executions. Pending means execution may not have started, may still be
running, or may have finished without a recorded outcome. SQLite and backend calls
cannot share an atomic transaction. A failed completion write returns ERROR and
withholds the backend response; it never retries the backend. The existing
`backend_called` field indicates successful backend return, including when the
subsequent audit completion write fails.

Initial audit failures prevent backend execution. Review-storage failures remain
closed. Monitoring storage failures return a generic HTTP 503, not empty metrics.
Each database operation uses a fresh connection, a bounded five-second lock wait,
transaction commit/rollback, and explicit closure (including on Windows). The audit
path is anchored to the repository, independent of the working directory.
Short `BEGIN IMMEDIATE` transactions serialize schema migration and provide a
consistent counts/recent-records snapshot. Transactions never span backend calls.
This trades some read/write concurrency for simple local SQLite behavior.

For normal Windows development, initialize the shared local monitoring token
once from the repository root:

```powershell
.\scripts\start-local.ps1 -Service Initialize
```

The launcher generates 32 random bytes and stores the token as a Windows
DPAPI-encrypted SecureString in `.env.monitoring`, restricted to the current
Windows account. This file is ignored by Git and is **not** a dotenv file.
Do not print, commit, copy, or replace it with plaintext. Decryption requires the
same Windows account on the same machine. The launcher loads the shared token
into each child process's environment without putting it in command arguments,
then restores its own previous environment when the command exits. The token is
necessarily available in the application process memory; DPAPI protects the
persisted copy, not a compromised Windows account.

Stop existing API and dashboard instances with Ctrl+C. In two separate PowerShell
terminals, run the following commands from the repository root:

```powershell
# Terminal 1
.\scripts\start-local.ps1 -Service Api
# Terminal 2
.\scripts\start-local.ps1 -Service Dashboard
```

In a third terminal, verify authentication and dashboard rendering without
displaying the token:

```powershell
.\scripts\start-local.ps1 -Service Verify
```

Expected: authenticated `/audit` is 200, missing/wrong credentials are 401,
and dashboard monitoring/refresh pass against the real port-8000 API. Open
`http://127.0.0.1:8501` and click **Refresh audit monitoring** after restarting.
The launcher deliberately reuses the encrypted token on later starts. To rotate
it, stop both services, remove only `.env.monitoring`, initialize again, and
restart both services. Do not run commands that dump the token or environment.

Keep both servers bound to loopback. Disable proxy-header trust as shown so
forwarded headers cannot change the peer used for access checks. This setup is
for a single-machine demo; do not place it behind a proxy or publish Streamlit
without designing authenticated access. The dashboard itself has no user login.
Ollama is a separate local service at `127.0.0.1:11434`, using `llama3.2:1b`;
its model availability must be checked separately. The app currently trains the
privacy model at startup using the existing local processed training CSV files.

Run the full automated suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use temporary audit/review databases and mocked backends; Ollama is not
required. Audit monitoring covers gateway requests, not `/analyze` or `/redact`.
The other existing API endpoints retain their local-development access model.
The SQLite journal is persistent, but is not a tamper-proof or externally replicated
audit system. Retention and archival are not automated. No n8n integration is used.

### Remaining work

- Live privacy warnings while users type prompts.
- Broader privacy/secret coverage, held-out evaluation, and ML calibration.
- Authenticated multi-user review and deployment hardening.
- Docker, CI/CD, monitoring, and broader independent evaluation.
