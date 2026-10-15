
import re


# 1. Original patterns: explicit PII disclosures
PII_PATTERNS = {
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    ),

    "PIN": re.compile(
        r"\b(?:my\s+)?(?:ATM\s+)?PIN\s*"
        r"(?:number\s*)?(?:is|:|=)\s*\d{4,6}\b",
        re.IGNORECASE,
    ),

    "ACCOUNT": re.compile(
        r"\b(?:my\s+)?account\s*"
        r"(?:number|no\.?|#)\s*"
        r"(?:is|:|=)?\s*\d{6,18}\b",
        re.IGNORECASE,
    ),

    "PHONE": re.compile(
        r"\b(?:my\s+)?(?:phone|mobile|contact)\s*"
        r"(?:number\s*)?(?:is|:|=)\s*"
        r"\+?\d[\d\s()-]{7,}\d\b",
        re.IGNORECASE,
    ),

    "ADDRESS": re.compile(
        r"\b(?:my\s+)?address\s*(?:is|:|=)\s*"
        r"\d{1,6}\s+[A-Za-z][A-Za-z\s.-]*?"
        r"\b(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr)\b",
        re.IGNORECASE,
    ),
}


# 2. Broader patterns: PII values near relevant keywords
CONTEXT_PATTERNS = {
    "PIN_CONTEXT": re.compile(
        r"\bPIN\b.{0,50}?\b\d{4,6}\b",
        re.IGNORECASE,
    ),

    "ACCOUNT_CONTEXT": re.compile(
        r"\baccount\b.{0,60}?\b\d{8,18}\b",
        re.IGNORECASE,
    ),

    "PHONE_CONTEXT": re.compile(
        r"\b(?:phone|mobile|contact)\b"
        r".{0,50}?\b\d{8,15}\b",
        re.IGNORECASE,
    ),

    "ADDRESS_CONTEXT": re.compile(
        r"\b(?:address|live|reside)\b"
        r".{0,60}?\b\d{1,6}\s+"
        r"[A-Za-z][A-Za-z\s.-]*?"
        r"\b(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr)\b",
        re.IGNORECASE,
    ),
}


# 3. Detect matches from both pattern groups
def detect_pii(text):
    matches = []

    all_patterns = {
        **PII_PATTERNS,
        **CONTEXT_PATTERNS,
    }

    for pii_type, pattern in all_patterns.items():
        for match in pattern.finditer(text):
            matches.append({
                "type": pii_type,
                "start": match.start(),
                "end": match.end(),
            })

    return matches


# 4. Return True when at least one pattern matches
def contains_pii(text):
    return len(detect_pii(text)) > 0


# 5. Quick local tests
if __name__ == "__main__":
    examples = [
        ("How can I change my PIN?", False),
        ("My PIN is 4826.", True),
        ("For my debit card, the PIN I selected was 3917.", True),
        ("I accidentally typed my PIN, 6504, into this chat.", True),
        ("What is a PIN used for?", False),
        ("My email is alex@example.com.", True),
        ("Can I update my email?", False),
        ("My account number is 123456789012.", True),
        ("The account receiving the funds is 837261904553.", True),
        ("My phone number is 9876543210.", True),
        ("My phone is broken.", False),
        ("My address is 24 King Street.", True),
        ("How do I update my address?", False),
    ]

    correct = 0

    for text, expected in examples:
        detected = contains_pii(text)
        matches = detect_pii(text)

        if detected == expected:
            correct += 1

        print("Text:", text)
        print("Expected:", expected)
        print("Detected:", detected)
        print("Types:", [m["type"] for m in matches])
        print("-" * 45)

    print(f"\nCorrect: {correct}/{len(examples)}")
