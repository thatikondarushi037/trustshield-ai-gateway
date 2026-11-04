# Reproducibility and benchmarking

Run all commands from the repository root. Runtime dependencies are fully version-pinned in `requirements.lock` (49 packages); this is not a hash-verified supply-chain lock. Windows Python 3.14 and Linux Python 3.13 were exercised. CPU-only CI builds public synthetic fixtures; original raw datasets and saved production weights are intentionally absent from Git.

## Software regression and control flow

```powershell
.\.venv\Scripts\python.exe -W error::ResourceWarning -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src.demo
.\.venv\Scripts\python.exe -m src.release_checks
git diff --check
docker compose config --quiet
docker build --target ci -t trustshield:ci .
docker run --rm --network none trustshield:ci python -m scripts.ci_verify
.\.venv\Scripts\python.exe scripts/verify_image.py
```

The CI target executes a source-only temporary copy, generates synthetic fixtures there, and runs the complete suite and deterministic demo. It never modifies local protected files. Standard Streamlit bare-test-context and upstream FastAPI/TestClient deprecation warnings are reported; they are not suppressed test failures. ResourceWarning is treated as an error. No platform-specific tests are skipped.

`verify_image.py` inspects every actual application image layer, including files later deleted, for forbidden raw datasets, private evidence, credentials and local databases. It requires a built `trustshield:1.0.0-rc1` image and temporary disk space for a Docker image archive. Optional live deployment verification uses `.\.venv\Scripts\python.exe scripts/verify_deployment.py --restart-container` against alternate port 18000 and the local ignored container secret. It deliberately adds four fictional audited requests and restarts only the API container, preserving its named volume.

## Private development evaluation (not available from a fresh public clone)

Only run with the existing protected corpora/artifact; do not replace them with invented evaluation data:

```powershell
.\.venv\Scripts\python.exe -m src.dataset_audit --help
.\.venv\Scripts\python.exe -m src.dataset_reliability --live-api http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m src.ml_experiments
.\.venv\Scripts\python.exe -m src.holdout_workflow validate
.\.venv\Scripts\python.exe -m src.devtools reports
```

Holdout validation is expected to return nonzero and NOT_READY. It checks an empty candidate; it does not collect/freeze examples. `--skip-contextual` allows baseline/calibration/robustness without Ollama weights. Missing protected inputs are a blocker, not permission to quote old measurements as a new run. `src.devtools reports` refreshes only an aggregate integrity index after report generation; it does not validate independence or sign evidence. `protected-check` uses the local ignored pre-session inventory and is a session verification utility, not a fresh-clone command.

The contextual experiment uses the already installed local encoder; no PyTorch package was installed. If unavailable, obtain a legally licensed compatible embedding model separately, record its exact digest and rerun; never invent a comparison. Calibration plot support is optional: install `requirements-experiments.txt` in a compatible experiment environment when needed. Hardware recorded locally: RTX 4060 Laptop, 8,188 MiB VRAM, 32 GB system RAM. Benchmark timing covers ten warmed identical requests and contextual HTTP overhead, not full gateway latency, concurrent load, cold starts or peak native memory. Input/model/tool hashes are in JSON; repeat runs may have different timing.

## Browser verification and screenshots

Keep optional browser dependencies isolated from production:

```powershell
py -3.13 -m venv .tools-venv
.\.tools-venv\Scripts\python.exe -m pip install playwright==1.64.1
.\.tools-venv\Scripts\python.exe -m playwright install chromium
.\.tools-venv\Scripts\python.exe scripts/verify_console.py
# Optional container console, after alternate-port startup:
.\.tools-venv\Scripts\python.exe scripts/verify_console.py --url http://127.0.0.1:18501 --screenshots .cache/container-screenshots
```

The script opens actual Chromium, visits all five sections, waits for completed rendering, checks real draft blocking without submission, captures empty-prompt/metadata screenshots and renders a mobile viewport. It does not test every browser, accessibility interaction or production authentication deployment. Review screenshots before publishing: no prompt, generated response, token or private annotation may appear.

GitHub Actions uses SHA-pinned actions, supported Python versions and a separate Docker build job, with no automatic deployment. Local syntax validation and equivalent test/container commands are evidence; an actual remote Actions run still requires an approved push.
