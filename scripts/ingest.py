"""Build the chunk index from CORPUS_PATH and persist it to INDEX_PATH."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from docs_rag.ingest.index import build_index
from docs_rag.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=None, help="override CORPUS_PATH")
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--chunk-overlap", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    index = build_index(
        settings,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        corpus_path=args.corpus,
    )
    if settings.vector_store == "memory":
        index.save(Path(settings.index_path))
        print(f"saved {len(index.chunks)} chunks to {settings.index_path}")
    else:
        print(f"stored {len(index.chunks)} chunks in {settings.vector_store}")
    print(index.meta)


if __name__ == "__main__":
    main()
