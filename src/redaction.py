from src.pii_rules import detect_pii


def redact_message(text: str) -> str:
    #  Detect sensitive information
    matches = detect_pii(text)

    if not matches:
        return text

    #  Sort matches by their starting position
    matches = sorted(
        matches,
        key=lambda match: match["start"]
    )

    #  Merge overlapping sensitive spans
    merged = []

    for match in matches:
        start = match["start"]
        end = match["end"]

        if not merged or start >= merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(
                merged[-1][1],
                end
            )

    #  Replace sensitive spans
    result = []
    current_position = 0

    for start, end in merged:
        result.append(text[current_position:start])
        result.append("[REDACTED]")
        current_position = end

    #  Preserve remaining non-sensitive text
    result.append(text[current_position:])

    return "".join(result)
