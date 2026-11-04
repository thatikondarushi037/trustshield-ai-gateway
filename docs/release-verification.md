# V1.0 release-candidate verification

Verification performed in the existing `feature/ml-evaluation` working tree, November 2026. No commit, push, merge or publication was performed. Previous uncommitted dataset/holdout milestones were preserved. This is a local portfolio release candidate, not independently validated privacy protection or a public deployment approval.

## Actual commands and observations

Commands below were executed from the repository root. Optional Playwright tools were installed in `.tools-venv`, isolated from the production environment. Docker Desktop used Linux containers. Existing production `.venv` was Python 3.14.5; container Python was 3.13.

| Command | Observed result |
|---|---|
| `.\.venv\Scripts\python.exe -W error::ResourceWarning -m unittest discover -s tests -v` | **130 tests, OK**; final Windows run 14.494 seconds |
| `docker build --target ci -t trustshield:ci .` | PASS; source-only fixture generation, **130 tests, OK**, 9.381 seconds, deterministic demo PASS |
| `docker run --rm --network none trustshield:ci python -m scripts.ci_verify` | Earlier equivalent source-only run: **130 tests, OK**, 9.723 seconds, demo PASS |
| `.\.venv\Scripts\python.exe -m src.dataset_reliability --live-api http://127.0.0.1:8000` | 7 datasets; **344 live analysis checks, zero mismatches**; 8,600 input-record privacy checks, zero raw-text matches; protected inputs unchanged |
| `.\.venv\Scripts\python.exe -m src.ml_experiments` | 7 datasets; contextual COMPLETE; sigmoid calibration evaluated; 80 robustness probes; production_updated false |
| `.\.venv\Scripts\python.exe -m src.holdout_workflow validate` | Expected nonzero **NOT_READY**; 0 records/eligible rows/source tracks/paired annotations; original strict floors retained |
| `.\.venv\Scripts\python.exe -m src.demo` | PASS; ALLOW, BLOCK, HOLD, secret BLOCK, safe backend failure; 5 finalized audits; rejection/order/persistence assertions PASS |
| `.\scripts\start-local.ps1 -Service Verify` | Authenticated `/audit` 200; absent/wrong token 401; persistent dashboard counts and refresh PASS |
| `.\.venv\Scripts\python.exe -m src.demo --live` | Actual local Ollama PASS; ALLOW, backend completed, nonempty response (444 characters in observed run); response text withheld |
| `docker compose config --quiet` | PASS |
| `docker compose build` | PASS; pinned base and dependency lock; final runtime uses public synthetic demo artifact |
| `$env:TRUSTSHIELD_API_PORT='18000'; $env:TRUSTSHIELD_DASHBOARD_PORT='18501'; docker compose up -d --wait` | API and dashboard healthy, bound only to 127.0.0.1:18000 and :18501 |
| `.\.venv\Scripts\python.exe scripts/verify_deployment.py --restart-container` | PASS on final image; all five service indicators UP; anonymous/wrong-token 401, authorized 200; four expected synthetic outcomes, metadata finalized, aggregate delta +4, exact metrics/IDs preserved across API restart |
| `.\.venv\Scripts\python.exe -m src.demo --live --api http://127.0.0.1:18000` | Actual host Ollama PASS from container gateway; final observed response 386 characters, text withheld |
| `.\.tools-venv\Scripts\python.exe scripts/verify_console.py` | Chromium PASS: all five sections, draft BLOCK without submission, mobile render, zero page errors |
| `.\.tools-venv\Scripts\python.exe scripts/verify_console.py --url http://127.0.0.1:18501 --screenshots .cache/container-screenshots` | Same browser checks PASS against actual container dashboard; archival metrics warning present |
| `.\.venv\Scripts\python.exe scripts/verify_image.py` | PASS: **14 image layers**, zero forbidden application files, including files hidden by later deletion |
| `docker run --rm --network none trustshield:1.0.0-rc1 python -c "import pathlib,os,json; assert not list(pathlib.Path('/app').rglob('*.csv')); print(json.dumps({'uid':os.getuid(),'raw_csv_files':0,'demo_artifact':pathlib.Path('/app/builtin/demo.joblib').is_file()}))"` | uid 1000, zero raw CSV files, demo artifact true |
| `docker run --rm --mount "type=bind,source=$((Get-Location).Path),target=/repo,readonly" --workdir /repo rhysd/actionlint:1.7.7 -color` | PASS, no diagnostics; image digest `sha256:887a259a5a534f3c4f36cb02dca341673c6089431057242cdc931e9f133147e9` |
| `.\.venv\Scripts\python.exe -m src.devtools protected-check` | **14 protected data/model files unchanged** against pre-session hash inventory |
| `.\.venv\Scripts\python.exe -m src.release_checks` | 8,660 available dataset-record checks; no prohibited candidate artifacts, detected credentials or full raw-text report matches. Candidate file count evolves as docs are added; use final output for exact inventory count |
| `git diff --check` | PASS |

Streamlit AppTest emits its upstream bare-context warnings; Linux FastAPI TestClient also emits an upstream HTTPX deprecation warning. No tests were skipped or weakened. ResourceWarning remained an error. GitHub Actions itself was not run remotely because no push was authorized; actionlint and equivalent local builds/tests are the available evidence.

## Defects found and fixed

- Development robustness probes exposed fullwidth and newline-context evasions. Narrow normalization/span and multiline-context fixes reduced withholding misses from 8/56 to 1/56 on the scored sensitive/credential probes; high safe withholding burden remains. Production artifact and threshold unchanged.
- Browser automation initially targeted the hidden native checkbox input; selecting the visible label fixed real interaction verification. Screenshot capture now waits for stale Streamlit elements to disappear and resets scroll position. This does not substitute a mocked UI for browser evidence.
- Image inspection found a legacy raw evaluation CSV admitted by a permissive parent-directory exception. Explicit child exclusion and report-file allowlisting corrected it. The rebuilt image was scanned layer by layer and reverified live. Earlier local build-cache images were not published; Docker cache management remains the machine owner's responsibility.

## Release assessment and remaining work

**Portfolio-ready local V1.0 release candidate:** working enforced flow, persistent metadata, polished verified console, actual Ollama execution, reproducible source-only tests, measured experiments, usable container deployment and honest evidence. It is not production-ready or a proven high-recall privacy detector.

Publication/release process: review the final working tree and documentation, explicitly approve a commit/push, and observe the first remote CI run. No automatic deployment is configured. A fresh public clone reproduces synthetic software tests and the demo; it cannot independently reproduce private historical corpus metrics without the protected inputs. Container archived reports clearly disclose their different runtime model.

Public-deployment blockers: user identity/authorization, TLS, quotas/rate limits, retention/backup/rotation design, stronger operational durability and a separate security review. Current classifier error rates preclude a strong privacy-protection claim. Audit finalization cannot roll back execution; local filesystem administrators can tamper with logs/secrets.

Independent-human tasks: author genuinely new fictional prompts without access to existing examples, register provenance and source tracks, provide two independent blinded annotations, adjudicate, review the changed precollection evaluation plan, satisfy 300 resolved examples and 30 connected groups per class plus two tracks, and authorize a valid freeze. None was fabricated or performed by Codex.

Optional research: span-level contextual models, multilingual/obfuscation evaluation, larger source-balanced development calibration, group-aware uncertainty intervals, selective-risk guarantees and drift/OOD detection. Do not tune on the future frozen holdout.

## Complete demonstration

Start Ollama and the two Windows launchers as described in README, then execute:

```powershell
.\.venv\Scripts\python.exe -m src.demo
.\.venv\Scripts\python.exe -m src.demo --live
.\scripts\start-local.ps1 -Service Verify
.\.tools-venv\Scripts\python.exe scripts/verify_console.py
```

Visit the workspace, analytics, review queue, ML evaluation and system health at http://127.0.0.1:8501 . Deterministic human-review demonstration rejects a ticket; a rewritten request must pass fresh checks. No unsafe approval is implemented. Genuine screenshots show empty prompts and metadata only. Manual review remains useful for browser/assistive-technology combinations, contrast preference, native mobile interaction and installation on another Windows account; these were not exhaustively verified.
