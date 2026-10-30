import re
from pathlib import Path

POLICIES_DIR = Path(__file__).parent.parent.parent / "data" / "policies"
POLICY_FILES = ["prices.md", "cancellations.md", "faq.md"]
TOP_N = 3

# words too common across all policy docs to be useful for ranking
STOP_WORDS = {"hours", "days", "day", "per", "the", "and", "for", "are", "with", "from"}

# Common word variations used in customer queries
WORD_VARIANTS = {
    "cancel": "cancellation",
    "cancels": "cancellation",
    "cancelled": "cancellation",
    "cancelling": "cancellation",
    "cancellations": "cancellation",
    "bookings": "booking",
    "reserve": "booking",
    "reservation": "booking",
    "reservations": "booking",
    "refunds": "refund",
    "refunded": "refund",
    "refunding": "refund",
    "paid": "pay",
    "payment": "pay",
    "payments": "pay",
    "bicycles": "bike",
    "bicycle": "bike",
    "bikes": "bike",
    "cycles": "bike",
    "opens": "open",
    "opening": "open",
    "opened": "open",
}


def normalize_word(word: str) -> str:
    return WORD_VARIANTS.get(word, word)


def load_policy(filename: str) -> str:
    path = POLICIES_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _split_into_sections(content: str) -> list[tuple[str, str]]:
    """Split markdown content into heading and body pairs."""
    sections = []
    current_heading = ""
    current_lines = []

    for line in content.splitlines():
        if line.startswith("#"):
            body = "\n".join(current_lines).strip()
            if current_heading and body:
                sections.append((current_heading, body))
            current_heading = line
            current_lines = []
        else:
            current_lines.append(line)

    body = "\n".join(current_lines).strip()
    if current_heading and body:
        sections.append((current_heading, body))

    return sections


def _score_section(heading: str, body: str, keywords: list[str]) -> int:
    """Score a section based on keyword matches. Heading matches count double."""
    words = {normalize_word(w) for w in re.findall(r"\b\w+\b", (heading + " " + body).lower())}
    heading_words = {normalize_word(w) for w in re.findall(r"\b\w+\b", heading.lower())}
    score = sum(1 for kw in keywords if kw in words)
    score += sum(2 for kw in keywords if kw in heading_words)
    return score


def search_policies(query: str) -> str:
    """Find the most relevant policy sections for a query"""
    if not query or not query.strip():
        return "No query provided."

    keywords = [
        normalize_word(word)
        for word in re.findall(r"\b\w+\b", query.lower())
        if len(word) > 2 and word not in STOP_WORDS
    ]

    scored = []

    for filename in POLICY_FILES:
        content = load_policy(filename)
        if not content:
            continue

        for heading, body in _split_into_sections(content):
            score = _score_section(heading, body, keywords)
            if score > 0:
                scored.append((score, filename, heading, body))

    if not scored:
        return "No relevant policy information found."

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0]
    top = [item for item in scored if item[0] >= 2 and item[0] >= best_score * 0.75][:TOP_N]

    if not top:
        top = scored[:1]

    parts = []
    for score, filename, heading, body in top:
        parts.append(f"--- {filename} ---")
        if heading:
            parts.append(heading)
        parts.append(body)
        parts.append("")

    return "\n".join(parts)
