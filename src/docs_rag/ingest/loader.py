"""Load Markdown and plain-text documents from a corpus directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docs_rag.textutil import first_heading

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}


@dataclass(frozen=True)
class Document:
    doc_path: str  # path relative to the corpus root, forward slashes
    title: str
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()


def load_corpus(root: Path) -> list[Document]:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {root}")
    docs: list[Document] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        title = first_heading(text) or path.stem.replace("-", " ").replace("_", " ").title()
        docs.append(Document(doc_path=rel, title=title, text=text))
    return docs
