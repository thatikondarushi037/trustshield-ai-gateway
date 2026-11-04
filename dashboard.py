
import streamlit as st
import httpx
import os

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="TrustShield AI Gateway",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ TrustShield AI Gateway")
st.caption("Privacy-Aware and Reliability-Aware AI Security Gateway")

if "history" not in st.session_state:
    st.session_state.history = []

prompt = st.text_area(
    "Enter an AI prompt",
    height=150,
    placeholder="Explain machine learning in simple words."
)

if st.button("Analyze and Submit", type="primary"):
    if not prompt.strip():
        st.warning("Enter a message first.")
    else:
        try:
            with st.spinner("Checking privacy and security..."):
                response = httpx.post(
                    f"{API_URL}/gateway/local",
                    json={"text": prompt},
                    timeout=90.0
                )
                response.raise_for_status()
                result = response.json()

            st.session_state.history.append({
                "decision": result["decision"],
                "types": result.get("detected_types", []),
                "secret_types": result.get("secret_types", [])
            })

            st.session_state.latest = result

        except httpx.ConnectError:
            st.error(
                "Cannot connect to FastAPI. "
                "Check whether port 8000 is running."
            )
        except httpx.TimeoutException:
            st.error(
                "Request timed out. "
                "The local AI model may be loading or responding slowly."
            )
        except httpx.HTTPStatusError as error:
            st.error(
                f"FastAPI returned HTTP {error.response.status_code}"
            )
        except httpx.HTTPError as error:
            st.error(f"HTTP request failed: {type(error).__name__}")


if "latest" in st.session_state:
    result = st.session_state.latest

    decision = result["decision"]

    if decision == "ALLOW":
        st.success("Request approved by configured security checks")
    elif decision == "BLOCK":
        st.error("Request blocked by TrustShield")
    elif decision == "HOLD":
        st.warning("Request held for review")
    else:
        st.warning("Request could not be completed")

    st.write("**Reason:**", result["reason"])
    st.write("**Detected PII:**", result.get("detected_types", []))
    st.write("**Detected secrets:**", result.get("secret_types", []))
    st.write("**Backend completed:**", result.get("backend_called", False))

    if result.get("response"):
        st.subheader("Local AI Response")
        st.write(result["response"])

st.divider()
st.subheader("Session Security Metrics")

history = st.session_state.history

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Requests", len(history))
col2.metric(
    "Allowed",
    sum(x["decision"] == "ALLOW" for x in history)
)
col3.metric(
    "Blocked",
    sum(x["decision"] == "BLOCK" for x in history)
)
col4.metric(
    "Held",
    sum(x["decision"] == "HOLD" for x in history)
)

st.caption(
    "Metrics are limited to this Streamlit session. "
    "Raw prompts are not stored in dashboard history."
)

st.divider()
st.subheader("Persistent Security Monitoring")
st.button("Refresh audit monitoring")
try:
    audit_token = os.environ.get("TRUSTSHIELD_AUDIT_TOKEN", "")
    if not audit_token:
        raise ValueError("Monitoring is disabled")
    audit_response = httpx.get(
        f"{API_URL}/audit", timeout=10.0,
        headers={"Authorization": f"Bearer {audit_token}"}
    )
    audit_response.raise_for_status()
    snapshot = audit_response.json()
    metrics = snapshot["metrics"]
    columns = st.columns(4)
    for column, key, label in zip(
        columns, ("total", "allowed", "blocked", "held"),
        ("Total Requests", "Allowed", "Blocked", "Held")
    ):
        column.metric(label, metrics[key])
    st.write("Failed executions / review writes:", metrics["failed"])
    st.write("Pending / unknown execution outcomes:", metrics["pending"])
    st.write("Recorded backend attempts:", metrics["backend_attempted"])
    st.write("Recorded backend successes:", metrics["backend_succeeded"])
    average_latency = metrics["average_latency_ms"]
    st.write("Average finalized gateway latency (ms):",
             round(average_latency, 2) if average_latency is not None else "No measurements")
    st.dataframe(snapshot["records"], use_container_width=True)
    st.caption("Persistent gateway metadata only. Pending does not imply success. "
               "Analysis and redaction calls are not included.")
except (httpx.HTTPError, ValueError, KeyError):
    st.warning("Persistent security monitoring is unavailable.")
