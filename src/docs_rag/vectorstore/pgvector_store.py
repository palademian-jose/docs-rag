"""Postgres + pgvector backend (optional extra: ``uv sync --extra pg``).

Same interface as the in-memory store. ``save``/``load`` are no-ops because Postgres is the
persistence. The table is created on first use; cosine distance is used for search.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from docs_rag.embeddings.base import l2_normalise


class PgVectorStore:
    kind = "pgvector"

    def __init__(self, dsn: str, dim: int, *, table: str = "chunks") -> None:
        try:
            import psycopg
            from pgvector.psycopg import register_vector
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("VECTOR_STORE=pgvector needs: uv sync --extra pg") from exc
        if not table.isidentifier():
            raise ValueError("table must be a plain identifier")
        self.table = table
        self.dim = dim
        self._conn = psycopg.connect(dsn, autocommit=True)
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self._conn)
        with self._conn.cursor() as cur:
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {self.table} "
                f"(id TEXT PRIMARY KEY, embedding vector({dim}) NOT NULL)"
            )

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        vectors = l2_normalise(np.asarray(vectors, dtype=np.float32))
        with self._conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO {self.table} (id, embedding) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding",
                [(cid, vec) for cid, vec in zip(ids, vectors, strict=True)],
            )

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        q = l2_normalise(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT id, 1 - (embedding <=> %s) AS score FROM {self.table} "
                "ORDER BY embedding <=> %s LIMIT %s",
                (q, q, k),
            )
            return [(str(row[0]), float(row[1])) for row in cur.fetchall()]

    def __len__(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table}")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(f"TRUNCATE {self.table}")

    def save(self, path: Path) -> None:
        return None

    def load(self, path: Path) -> None:
        return None
