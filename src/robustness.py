"""Fictional DEVELOPMENT probes. Never an independent holdout or training input."""
import json
import unicodedata
from collections import Counter
from pathlib import Path

from src.dataset_reliability import binary_metrics, digest
from src.policy_engine import enforce_policy
from src.privacy_decision_engine import analyze_message


def development_probes():
    # Text exists only in code and process memory; reports export no text/values.
    seeds = [
        ("safe_discussion", "What is a PIN used for?", 0, 0),
        ("email", "My email is fictional.robustness@example.com.", 1, 1),
        ("pin", "My PIN is 4826.", 1, 1),
        ("context", "For my debit card, the PIN I selected was 3917.", 1, 1),
        ("negation_discussion", "I will not disclose a PIN or account number.", 0, 0),
        ("negation_disclosure", "Do not share my email: fictional.robustness@example.com.", 1, 1),
        ("secret", "api_key = fictional_nonfunctional_robustness_123", 0, 1),
        ("mixed", "My PIN is 4826 and my email is fictional.robustness@example.com.", 1, 1),
        ("unfamiliar", "The four digits I use to unlock my banking card are 7281.", 1, 1),
        ("masked", "My PIN is **** and my email is [hidden].", None, None),
    ]
    variations = {
        "original": lambda s: s,
        "whitespace": lambda s: s.replace(" ", "  \t"),
        "newlines": lambda s: s.replace(" ", "\n"),
        "punctuation": lambda s: s.replace(" is ", " = "),
        "fullwidth": lambda s: "".join(chr(ord(c) + 0xFEE0) if 33 <= ord(c) <= 126 else c for c in s),
        "nfkc_recovery": lambda s: unicodedata.normalize("NFKC", "".join(chr(ord(c) + 0xFEE0) if 33 <= ord(c) <= 126 else c for c in s)),
        "long_prefix": lambda s: ("General fictional background. " * 600) + s,
        "long_suffix": lambda s: s + (" General fictional background." * 600),
    }
    return [{"id": f"{name}:{kind}", "family": name, "variation": kind, "text": transform(text),
             "privacy_label": privacy, "withholding_label": withholding}
            for name, text, privacy, withholding in seeds for kind, transform in variations.items()]


def run_robustness(model, root):
    probes = development_probes()
    rows = []
    for case in probes:
        analysis = analyze_message(case["text"], model)
        policy = enforce_policy(case["text"], analysis)
        rows.append({"case": case, "ml": int(model.predict([case["text"]])[0]),
                     "hybrid": int(analysis["decision"] != "SAFE"),
                     "policy": int(not policy["forward_allowed"]), "decision": policy["decision"]})
    def summarize(group):
        valid = [row for row in group if row["case"]["privacy_label"] is not None]
        withheld = [row for row in group if row["case"]["withholding_label"] is not None]
        return {"cases": len(group), "unscored_ambiguous": len(group) - len(valid),
                "ml_only": binary_metrics([r["case"]["privacy_label"] for r in valid], [r["ml"] for r in valid]),
                "hybrid_non_safe": binary_metrics([r["case"]["privacy_label"] for r in valid], [r["hybrid"] for r in valid]),
                "gateway_withholding": binary_metrics([r["case"]["withholding_label"] for r in withheld], [r["policy"] for r in withheld]),
                "decisions": dict(Counter(r["decision"] for r in group)),
                "miss_references": [r["case"]["id"] for r in withheld if r["case"]["withholding_label"] == 1 and r["policy"] == 0][:5]}
    report = {"status": "COMPLETE", "artifact_sha256": digest(root / "models/privacy_model_v02.joblib"),
              "rule_sha256": {name: digest(root / name) for name in ("src/pii_rules.py", "src/secret_detector.py", "src/text_normalization.py")},
              "tool_sha256": digest(Path(__file__)), "development_only": True,
              "limitations": "Generated correlated probes, not independent evidence. Masked cases have unknown ground truth and are excluded from binary metrics. Credential withholding is separate from privacy labels.",
              "overall": summarize(rows),
              "variations": {kind: summarize([r for r in rows if r["case"]["variation"] == kind]) for kind in sorted({r["case"]["variation"] for r in rows})}}
    payload = json.dumps(report)
    if any(p["text"] in payload for p in probes):
        raise ValueError("Report privacy check failed")
    return report
