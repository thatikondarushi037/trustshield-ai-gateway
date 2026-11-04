"""Deterministic isolated gateway demo; optional genuine live-Ollama check."""
import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import httpx
from src import audit_logger, review_queue
from src.gateway_service import process_request


def deterministic_demo():
    with tempfile.TemporaryDirectory() as folder, \
         patch.object(audit_logger, "DB_PATH", Path(folder) / "audit.db"), \
         patch.object(review_queue, "DB_PATH", Path(folder) / "reviews.db"):
        def backend(text):
            assert audit_logger.monitoring_snapshot()["records"][0]["execution_status"] == "PENDING"
            return "Deterministic demonstration response."
        called = Mock(side_effect=backend)
        outcomes = []
        cases = [("safe", "Explain machine learning.", "SAFE", "ALLOW"),
                 ("sensitive", "My email is demo@example.com.", "SENSITIVE", "BLOCK"),
                 ("hold", "Contextual privacy uncertainty", "REVIEW", "HOLD"),
                 ("secret", "api_key = fictional_nonfunctional_demo_key", "SAFE", "BLOCK")]
        for label, text, classification, expected in cases:
            before = called.call_count
            with patch("src.gateway_service.analyze_message", return_value={"decision": classification, "detected_types": []}):
                result = process_request(text, None, called)
            assert result["decision"] == expected
            assert called.call_count - before == int(expected == "ALLOW")
            if expected == "HOLD":
                assert review_queue.resolve_review(result["review_id"], "REJECTED")
                assert not review_queue.list_reviews()
            outcomes.append({"case": label, "decision": result["decision"], "backend_completed": result["backend_called"]})
        with patch("src.gateway_service.analyze_message", return_value={"decision": "SAFE", "detected_types": []}):
            failed = process_request("Fictional backend failure exercise", None, Mock(side_effect=RuntimeError("fictional private exception")))
        assert failed["decision"] == "ERROR" and "fictional private exception" not in str(failed)
        outcomes.append({"case": "backend_failure", "decision": "ERROR", "backend_completed": False})
        snapshot = audit_logger.monitoring_snapshot()
        assert snapshot["metrics"]["total"] == 5 and snapshot["metrics"]["failed"] == 1
        # Fresh connection proves persistence rather than merely reading an in-memory log.
        assert audit_logger.monitoring_snapshot() == snapshot
        return {"status": "PASS", "classification": "Injected decisions for deterministic control-flow verification; not ML evaluation",
                "outcomes": outcomes, "audit_metrics": snapshot["metrics"], "review_rejection": "PASS", "backend_ordering": "PASS"}


def live_demo(base_url):
    # Real service, current model and Ollama. Never fake success or print generated text.
    with httpx.Client(base_url=base_url, timeout=100, trust_env=False) as client:
        response = client.post("/gateway/local", json={"text": "Explain machine learning in two short sentences."})
        response.raise_for_status()
        data = response.json()
        passed = data.get("decision") == "ALLOW" and data.get("backend_called") and bool(data.get("response"))
        return {"status": "PASS" if passed else "NOT_COMPLETED", "decision": data.get("decision"),
                "backend_completed": data.get("backend_called", False), "response_characters": len(data.get("response") or ""),
                "audit_id": data.get("audit_id")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        result = live_demo(args.api) if args.live else deterministic_demo()
    except (httpx.HTTPError, ValueError):
        result = {"status": "NOT_COMPLETED", "reason": "Live services unavailable; private errors withheld"}
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
