"""Build, persist and load the chunk index (chunks + dense vectors)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from docs_rag.embeddings import Embedder, get_embedder
from docs_rag.ingest.chunking import Chunk, chunk_documents
from docs_rag.ingest.loader import load_corpus
from docs_rag.settings import Settings, get_settings
from docs_rag.vectorstore import VectorStore, get_vector_store

log = logging.getLogger(__name__)


@dataclass
class Index:
    chunks: list[Chunk]
    store: VectorStore
    embedder: Embedder
    chunk_size: int
    chunk_overlap: int
    corpus_path: str
    by_id: dict[str, Chunk] = field(init=False)

    def __post_init__(self) -> None:
        self.by_id = {c.chunk_id: c for c in self.chunks}

    @property
    def meta(self) -> dict:
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "corpus_path": self.corpus_path,
            "embedding_model": self.embedder.model_name,
            "embedding_dim": self.embedder.dim,
            "n_chunks": len(self.chunks),
        }

    def save(self, index_path: Path) -> None:
        index_path = Path(index_path)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        self.store.save(index_path)
        sidecar = _sidecar(index_path)
        sidecar.write_text(
            json.dumps({"meta": self.meta, "chunks": [c.to_dict() for c in self.chunks]}),
            encoding="utf-8",
        )


def _sidecar(index_path: Path) -> Path:
    return index_path.with_suffix(".chunks.json")


def build_index(
    settings: Settings | None = None,
    *,
    embedder: Embedder | None = None,
    store: VectorStore | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    corpus_path: Path | None = None,
) -> Index:
    settings = settings or get_settings()
    embedder = embedder or get_embedder(settings)
    size = chunk_size or settings.chunk_size
    overlap = settings.chunk_overlap if chunk_overlap is None else chunk_overlap
    corpus = Path(corpus_path or settings.corpus_path)
    docs = load_corpus(corpus)
    chunks = chunk_documents(docs, size=size, overlap=overlap)
    store = store or get_vector_store(embedder.dim, settings)
    store.clear()
    if chunks:
        vectors = embedder.embed([c.embed_text for c in chunks])
        store.add([c.chunk_id for c in chunks], vectors)
    log.info(
        "indexed %d documents into %d chunks (size=%d overlap=%d)",
        len(docs),
        len(chunks),
        size,
        overlap,
    )
    return Index(chunks, store, embedder, size, overlap, corpus.as_posix())


def load_index(
    settings: Settings | None = None, *, embedder: Embedder | None = None
) -> Index | None:
    """Load a persisted index if it exists and matches the current settings, else None."""
    settings = settings or get_settings()
    index_path = Path(settings.index_path)
    sidecar = _sidecar(index_path)
    if settings.vector_store != "memory" or not index_path.exists() or not sidecar.exists():
        return None
    embedder = embedder or get_embedder(settings)
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    if (
        meta.get("chunk_size") != settings.chunk_size
        or meta.get("chunk_overlap") != settings.chunk_overlap
        or meta.get("embedding_model") != embedder.model_name
        or meta.get("corpus_path") != Path(settings.corpus_path).as_posix()
    ):
        log.info("persisted index does not match settings; it will be rebuilt")
        return None
    store = get_vector_store(embedder.dim, settings)
    store.load(index_path)
    chunks = [Chunk.from_dict(c) for c in data["chunks"]]
    return Index(
        chunks, store, embedder, settings.chunk_size, settings.chunk_overlap, meta["corpus_path"]
    )


def load_or_build_index(settings: Settings | None = None, *, persist: bool = True) -> Index:
    settings = settings or get_settings()
    index = load_index(settings)
    if index is None:
        index = build_index(settings)
        if persist and settings.vector_store == "memory":
            index.save(Path(settings.index_path))
    return index
