"""Compatibility-character matching view with offsets into the original text.

Per-codepoint NFKC deliberately avoids claiming complete Unicode canonicalization.
It handles fullwidth forms/ligatures without corrupting redaction offsets.
"""
import unicodedata


def matching_view(text):
    pieces, positions = [], []
    for index, char in enumerate(text):
        normalized = unicodedata.normalize("NFKC", char)
        pieces.append(normalized)
        positions.extend([index] * len(normalized))
    return "".join(pieces), positions


def original_span(start, end, positions):
    return positions[start], positions[end - 1] + 1
