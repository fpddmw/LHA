"""Count actual card and surrounding-text changes, not declared topic operations."""
import re


def blocks(row, text):
    cards = row.get("cards", []) if row else []
    if not cards:
        return {"legacy-topic:" + row["id"]: text} if row and text else {}
    if len(cards) == 1:
        return {cards[0]["id"]: {"text": text, "metadata": cards[0], "claims": row.get("claims", [])}}
    starts = []
    for card in cards:
        pattern = r"(?m)^###\s+" + re.escape(card["id"]) + r"(?:\s|[·:])[^\n]*$"
        match = re.search(pattern, text)
        if not match:
            raise ValueError("Multiple cards need individually addressable '### ID' sections")
        starts.append((match.start(), card))
    starts.sort(key=lambda x: x[0])
    result = {"topic-context:" + row["id"]: {"text": text[:starts[0][0]], "claims": row.get("claims", [])}}
    for i, (start, card) in enumerate(starts):
        result[card["id"]] = {"text": text[start:starts[i+1][0] if i+1 < len(starts) else len(text)], "metadata": card}
    return result


def changed_cards(old, old_text, change):
    before = blocks(old, old_text)
    after = {} if change["operation"] == "delete" else blocks(change, change.get("text", ""))
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
