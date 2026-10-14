"""Small, dependency-free text helpers shared by the fake backends, BM25 and the lexical judge."""

from __future__ import annotations

import re
from collections.abc import Iterable

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")

STOPWORDS: frozenset[str] = frozenset(
    [
        # articles, conjunctions, prepositions
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "of", "for", "to", "in",
        "on", "at", "by", "with", "from", "as", "into", "through", "under", "until", "up",
        "about", "above", "after", "again", "against", "before", "below", "between", "both",
        "down", "during", "each", "few", "further", "off", "once", "only", "other", "out",
        "over", "own", "same", "some", "such", "than", "too", "very", "so", "nor", "not", "no",
        # pronouns and determiners
        "it", "its", "this", "that", "these", "those", "there", "here", "he", "her", "hers",
        "him", "his", "i", "me", "my", "myself", "our", "ours", "she", "their", "theirs",
        "them", "they", "we", "you", "your", "yours", "all", "any", "most", "more",
        # verbs and auxiliaries
        "is", "are", "was", "were", "be", "been", "being", "am", "do", "does", "did", "done",
        "doing", "can", "could", "should", "would", "may", "might", "must", "shall", "will",
        "had", "has", "have", "having", "says", "say", "said",
        # question words and generic nouns that carry no signal in this corpus
        "what", "which", "who", "whom", "whose", "when", "where", "why", "how", "because",
        "just", "s", "t", "page", "handbook", "section", "according",
    ]
)  # fmt: skip


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens with light plural stripping; keeps hyphenated identifiers."""
    out: list[str] = []
    for tok in _TOKEN_RE.findall(text.lower()):
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        out.append(tok)
    return out


def content_tokens(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in STOPWORDS and len(t) > 1]


def overlap_ratio(query_tokens: Iterable[str], doc_tokens: Iterable[str]) -> float:
    """Fraction of distinct query tokens that appear in the document."""
    q = set(query_tokens)
    if not q:
        return 0.0
    d = set(doc_tokens)
    return len(q & d) / len(q)


def is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line))


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences; list items and headings become their own units."""
    units: list[str] = []
    paragraph: list[str] = []
    in_fence = False

    def flush() -> None:
        if paragraph:
            merged = " ".join(paragraph)
            units.extend(s.strip() for s in _SENTENCE_RE.split(merged) if s.strip())
            paragraph.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            flush()
            continue
        if in_fence:
            continue
        if not line or set(line) <= {"-", "|", ":", " "}:
            flush()
            continue
        if line.startswith(("- ", "* ", "|")) or re.match(r"^\d+\.\s", line):
            flush()
            item = line.strip("|").strip().lstrip("-* ").strip()
            item = re.sub(r"^\d+\.\s+", "", item)
            if item:
                units.append(item)
            continue
        if _HEADING_RE.match(line):
            flush()
            continue
        paragraph.append(line)
    flush()
    return units


def heading_of(text: str) -> str | None:
    """Return the last Markdown heading that appears in the text, if any."""
    heading = None
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            heading = m.group(1).strip()
    return heading


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            return m.group(1).strip()
    return None
