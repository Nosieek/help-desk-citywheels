import re
from pathlib import Path

from rank_bm25 import BM25Okapi

POLICIES_DIR = Path(__file__).parent.parent.parent / "data" / "policies"
POLICY_FILES = ["prices.md", "cancellations.md", "faq.md"]
TOP_N = 3

# true synonyms only - plural/tense variants are handled by _stem
SYNONYMS = {
    "bicycle": "bike",
    "bicycles": "bike",
    "cycle": "bike",
    "cycles": "bike",
    "reservation": "booking",
    "reservations": "booking",
    "reserve": "booking",
    "cost": "price",
    "costs": "price",
    "reschedule": "change",
    "rescheduling": "change",
    "paid": "pay",
    "payment": "pay",
    "payments": "pay",
}

_SUFFIXES = ("ations", "ation", "ings", "ing", "ies", "ied", "ed", "s")


def _stem(word: str) -> str:
    """
    Light suffix-stripping stemmer, applied to both documents and queries.

    Maps word forms to a common stem: prices/price -> pric,
    cancelled/cancellation/cancelling -> cancel, policies/policy -> policy.
    """
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            if suffix in ("ies", "ied"):
                word = word[: -len(suffix)] + "y"
            else:
                word = word[: -len(suffix)]
            break
    if word.endswith("e"):
        word = word[:-1]
    # collapse doubled final consonant: cancell -> cancel
    if len(word) > 3 and word[-1] == word[-2]:
        word = word[:-1]
    return word


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"\b\w+\b", text.lower())
    return [_stem(SYNONYMS.get(word, word)) for word in words]


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


def search_policies(query: str) -> str:
    """Find the most relevant policy sections for a query using BM25."""
    if not query or not query.strip():
        return "No query provided."

    sections = []
    for filename in POLICY_FILES:
        content = load_policy(filename)
        if not content:
            continue
        for heading, body in _split_into_sections(content):
            sections.append((filename, heading, body))

    if not sections:
        return "No relevant policy information found."

    # heading tokens counted twice: a match in the heading matters more
    corpus = [_tokenize(heading) * 2 + _tokenize(body) for _, heading, body in sections]
    scores = BM25Okapi(corpus).get_scores(_tokenize(query))

    ranked = sorted(range(len(sections)), key=lambda i: scores[i], reverse=True)
    top = [sections[i] for i in ranked[:TOP_N] if scores[i] > 0]

    if not top:
        return "No relevant policy information found."

    parts = []
    for filename, heading, body in top:
        parts.append(f"--- {filename} ---")
        parts.append(heading)
        parts.append(body)
        parts.append("")

    return "\n".join(parts)
