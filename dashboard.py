"""Local TrustShield security console. Enforcement remains server-side."""
import httpx
import pandas as pd
import streamlit as st
from src.console_client import api_request, safe_get

st.set_page_config(page_title="TrustShield | Security Operations", layout="wide")
st.markdown("""<style>
.stApp{background:#0b101b;color:#e5edf6}
[data-testid="stSidebar"]{background:#101827;border-right:1px solid #243049}
.block-container{max-width:1400px;padding-top:3.5rem}h1,h2,h3{letter-spacing:-.025em}
[data-testid="stMetric"]{background:#131e30;border:1px solid #27364e;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"]{color:#a7b7cc}
.eyebrow{color:#5bd5c7;font:600 .8rem monospace;letter-spacing:.15em}
.subtitle{color:#9aacbf;margin-bottom:1.8rem}.stButton>button{border-radius:8px}
</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### TrustShield")
    st.caption("AI SECURITY OPERATIONS")
    page = st.radio("Workspace", ["Prompt workspace", "Security analytics", "Review queue", "ML evaluation", "System health"], label_visibility="collapsed")
    st.divider()
    st.caption("V1.0 release candidate / local development")
    st.caption("Server policy is authoritative. No reviewer approval bypass exists.")
    st.button("Refresh console", width="stretch")
titles = {
    "Prompt workspace": ("Inspect before you send", "Privacy and credential checks before approved local AI execution."),
    "Security analytics": ("Security analytics", "Persistent policy decisions and observed execution outcomes."),
    "Review queue": ("Human review queue", "Metadata-only tickets. Revised inputs must pass every security check again."),
    "ML evaluation": ("Evidence, not assurances", "Verified local development reports with explicit statistical limitations."),
    "System health": ("Service health", "API, model availability, audit storage and review storage.")}
st.markdown('<div class="eyebrow">TRUSTSHIELD / SECURITY OPERATIONS</div>', unsafe_allow_html=True)
st.title(titles[page][0])
st.markdown(f'<div class="subtitle">{titles[page][1]}</div>', unsafe_allow_html=True)

def draft_check():
    st.session_state.pop("preview", None)
    st.session_state.pop("preview_error", None)
    if st.session_state.get("draft_checks") and st.session_state.get("prompt", "").strip():
        try:
            st.session_state.preview = api_request("POST", "/preview", {"text": st.session_state.prompt})
        except (httpx.HTTPError, ValueError, OSError):
            st.session_state.preview_error = True

if page == "Prompt workspace":
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.checkbox("Check draft on edit", key="draft_checks", on_change=draft_check,
                    help="Checks committed edits (blur or Ctrl+Enter), not every keystroke. Never contacts Ollama.")
        prompt = st.text_area("Prompt", key="prompt", height=210, max_chars=20000, on_change=draft_check,
                              placeholder="Use fictional content for demonstrations.")
        backend = st.selectbox("Execution backend", ["Local Ollama", "Deterministic demo"])
        if st.button("Analyze and submit", type="primary"):
            if not prompt.strip():
                st.warning("Enter a prompt first.")
            else:
                try:
                    with st.spinner("Applying gateway policy..."):
                        st.session_state.latest = api_request("POST", "/gateway/local" if backend == "Local Ollama" else "/gateway", {"text": prompt})
                except (httpx.HTTPError, ValueError, OSError):
                    st.error("Request unavailable. Check service health; no automatic retry was made.")
        st.caption("Drafts and responses stay in this UI session, not audit storage. Every submission receives fresh server checks.")
    with right:
        st.subheader("Policy outcome")
        if st.session_state.get("preview"):
            preview = st.session_state.preview
            st.info(f"Draft check: {preview['decision']} / {preview['reason']}")
        if st.session_state.get("preview_error"):
            st.caption("Draft preview unavailable; submission still requires server checks.")
        result = st.session_state.get("latest")
        if result:
            decision = result["decision"]
            render = st.success if decision == "ALLOW" else st.error if decision in ("BLOCK", "ERROR") else st.warning
            render(f"{decision} / {result['reason']}")
            st.write("PII categories", result.get("detected_types", []))
            st.write("Credential categories", result.get("secret_types", []))
            st.metric("Backend completed", "Yes" if result.get("backend_called") else "No")
            for key, label in (("audit_id", "Audit reference"), ("review_id", "Review reference")):
                if result.get(key):
                    st.caption(label + ": " + result[key])
        else:
            st.info("Submit a fictional prompt to see an explainable decision.")
    if st.session_state.get("latest", {}).get("response"):
        st.subheader("Backend response")
        st.text(st.session_state.latest["response"])

elif page == "Security analytics":
    snapshot = safe_get("/audit?limit=100", protected=True)
    if snapshot is None:
        st.warning("Persistent security monitoring is unavailable. Check authentication and service health.")
    else:
        metrics = snapshot["metrics"]
        for column, key, label in zip(st.columns(4), ("total", "allowed", "blocked", "held"), ("Requests", "Allowed", "Blocked", "Held")):
            column.metric(label, metrics[key])
        attempts, successes = metrics["backend_attempted"], metrics["backend_succeeded"]
        a, b, c = st.columns(3)
        a.metric("Recorded backend success rate", f"{successes / attempts:.1%}" if attempts else "No attempts")
        b.metric("Recorded backend failure rate", f"{(attempts - successes) / attempts:.1%}" if attempts else "No attempts")
        c.metric("Average gateway latency", f"{metrics['average_latency_ms']:.1f} ms" if metrics["average_latency_ms"] is not None else "No measurements")
        st.caption(f"Pending / unknown: {metrics['pending']} | Execution/review failures: {metrics['failed']}. ALLOW is a policy decision, not backend success.")
        chart, table = st.columns([1, 2])
        with chart:
            st.subheader("Policy distribution")
            st.bar_chart(pd.DataFrame({"Requests": [metrics[k] for k in ("allowed", "blocked", "held")]}, index=["ALLOW", "BLOCK", "HOLD"]), color="#53cfc2")
        with table:
            st.subheader("Recent audit records")
            if snapshot["records"]:
                st.dataframe(snapshot["records"], width="stretch", hide_index=True)
            else:
                st.info("No audited gateway requests yet.")
        if snapshot["records"]:
            points = pd.DataFrame(snapshot["records"])
            if points["latency_ms"].notna().any():
                st.subheader("Recent finalized gateway latency")
                st.line_chart(points.dropna(subset=["latency_ms"]).sort_values("created_at").set_index("created_at")[["latency_ms"]], color="#53cfc2")

elif page == "Review queue":
    status = st.selectbox("Ticket status", ["PENDING", "REJECTED", "REWRITE_REQUESTED"])
    tickets = safe_get("/reviews?status=" + status, protected=True)
    if tickets is None:
        st.warning("Review metadata unavailable. Check authentication and storage health.")
    elif not tickets["records"]:
        st.info("No tickets with this status.")
    else:
        st.metric("Visible tickets", len(tickets["records"]))
        st.dataframe(tickets["records"], width="stretch", hide_index=True)
    st.caption("Raw prompts are not retained. Local review supports rejection or rewrite only; it cannot approve forwarding.")

elif page == "ML evaluation":
    response = safe_get("/reports", protected=True)
    reports = response.get("reports", {}) if response else {}
    if not reports:
        st.warning("No verified current reports are available. Generate and verify reports before interpreting performance.")
    else:
        st.warning("Independent holdout: NOT READY. Measurements use development-exposed or uncertain-independence data.")
        if response.get("archival_display"):
            st.info("Archived measured reports: their original inputs/model are not the current container runtime. These are not fresh container benchmarks.")
        experiment = reports.get("ml_experiments.json", {})
        baseline = experiment.get("datasets", reports.get("dataset_reliability.json", {}).get("datasets", {}))
        if baseline:
            choices = sorted(baseline)
            dataset = st.selectbox("Evaluation dataset", choices, index=choices.index("legacy_test") if "legacy_test" in choices else 0)
            data = baseline[dataset]
            mode = st.radio("Detector view", ["Hybrid non-SAFE", "ML only"], horizontal=True)
            values = data["hybrid_non_safe" if mode == "Hybrid non-SAFE" else "ml_only"]
            for column, key, label in zip(st.columns(5), ("precision", "recall", "f1", "false_positive_rate", "false_negative_rate"), ("Precision", "Recall", "F1", "FPR", "FNR")):
                column.metric(label, f"{values[key]:.1%}" if values[key] is not None else "Undefined")
            st.caption("Hybrid non-SAFE includes REVIEW as abstention, not confirmed disclosure. ML-only uses the frozen saved artifact.")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Binary confusion matrix")
                st.dataframe(pd.DataFrame(values["confusion_matrix"], index=["Actual SAFE", "Actual SENSITIVE"], columns=["Predicted negative", "Predicted positive"]), width="stretch")
            with c2:
                st.subheader("Three-way hybrid decisions")
                st.dataframe(pd.DataFrame(data["hybrid_decision_matrix"], index=["Actual SAFE", "Actual SENSITIVE"], columns=["SAFE", "REVIEW", "SENSITIVE"]), width="stretch")
            comparison = experiment.get("contextual", {})
            st.subheader("Contextual model comparison")
            if comparison.get("status") == "COMPLETE" and dataset in comparison["datasets"]:
                st.dataframe(pd.DataFrame(comparison["datasets"][dataset]).T[["precision", "recall", "f1", "false_positive_rate", "false_negative_rate"]], width="stretch")
                st.caption(comparison["comparability"])
                benchmark = comparison["benchmark"]
                st.dataframe(pd.DataFrame({name: benchmark[name] for name in ("frozen_baseline", "contextual")}).T[["median_ms", "p95_ms", "python_peak_allocated_bytes"]], width="stretch")
                st.caption(benchmark["scope"] + " Memory excludes Ollama and native allocations.")
            else:
                st.info("Contextual comparison unavailable or not executed.")
        calibration = experiment.get("calibration", {})
        if "before" in calibration:
            st.subheader("Calibration experiment / not deployed")
            st.dataframe(pd.DataFrame({method: {k: calibration[method][k] for k in ("brier_score", "log_loss", "expected_calibration_error")} for method in ("before", "after")}).T, width="stretch")
            st.caption(f"Fit: {calibration['fit_dataset']}; evaluation: {calibration['evaluation_dataset']}. Historical group lineage remains uncertain.")

else:
    basic = safe_get("/health")
    health = safe_get("/operations/health", protected=True)
    for column, key, label in zip(st.columns(5), ("api", "ollama", "generation_model", "audit", "reviews"), ("FastAPI", "Ollama", "Generation model", "Audit monitoring", "Review storage")):
        state = health.get(key, "UNKNOWN") if health else ("UP" if key == "api" and basic else "UNKNOWN")
        column.metric(label, state)
    if health is None:
        st.warning("Protected checks need a configured monitoring credential. UNKNOWN does not mean healthy.")
    st.info("Point-in-time checks. Model availability does not guarantee generation latency or success.")
