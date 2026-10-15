import random
import pandas as pd

random.seed(42)

CATEGORY_CONFIG = {
    "email": {
        "values": [
            "alex@example.com",
            "sam@example.org",
            "taylor@example.net"
        ],
        "pairs": [
            (
                "Please update my email address.",
                "Please update my email address to {value}."
            ),
            (
                "I need to verify my contact email.",
                "I need to verify my contact email: {value}."
            )
        ]
    },

    "pin": {
        "values": ["4826", "7391", "2658"],
        "pairs": [
            (
                "Please help me reset my PIN.",
                "Please help me reset my PIN. It is {value}."
            ),
            (
                "I need to change my ATM PIN.",
                "I need to change my ATM PIN from {value}."
            )
        ]
    },

    "account": {
        "values": [
            "123456789012",
            "987654321098",
            "456789123012"
        ],
        "pairs": [
            (
                "How do I update my account number?",
                "How do I update my account number {value}?"
            ),
            (
                "Please check my account details.",
                "Please check my account {value}."
            )
        ]
    }
}


