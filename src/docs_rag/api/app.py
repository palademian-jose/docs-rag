"""FastAPI application: POST /ask, GET /health, GET /docs/{path} and the single-page UI.

Every request to /ask passes a per-IP token bucket and the daily USD cost cap before any model
call is made; both return HTTP 429 with a Retry-After header.
"""

from __future__ import annotations

import html
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from docs_rag import __version__
from docs_rag.generation.answer import Citation
from docs_rag.limits import RateLimiter
from docs_rag.pipeline import CostCapError, RAGPipeline
from docs_rag.settings import Settings, get_settings

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    refused: bool
    refusal_reason: str | None = None
    trace_id: str
    latency_ms: float
    cost_usd: float
    cache_hit: bool = False
    confidence: float = 0.0


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _resolve_doc(corpus_root: Path, rel_path: str) -> Path:
    """Resolve a citation path inside the corpus, rejecting traversal outside it."""
    root = corpus_root.resolve()
    candidate = (root / rel_path).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="document not found")
    return candidate


def render_doc_html(rel_path: str, text: str, highlight: tuple[int, int] | None = None) -> str:
    lines = text.splitlines() or [""]
    rows: list[str] = []
    for n, line in enumerate(lines, start=1):
        cls = " hl" if highlight and highlight[0] <= n <= highlight[1] else ""
        rows.append(
            f'<tr id="L{n}" class="line{cls}"><td class="n"><a href="#L{n}">{n}</a></td>'
            f'<td class="c">{html.escape(line) or "&nbsp;"}</td></tr>'
        )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(rel_path)}</title>
<style>
body{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;margin:0;
background:#fafafa;color:#222}}
header{{padding:10px 16px;background:#1f2937;color:#fff;font-family:system-ui,sans-serif}}
header a{{color:#93c5fd;text-decoration:none}}
table{{border-collapse:collapse;width:100%}}
td{{padding:1px 8px;vertical-align:top;white-space:pre-wrap}}
td.n{{width:3em;text-align:right;color:#999;user-select:none}}
td.n a{{color:inherit;text-decoration:none}}
tr.hl td{{background:#fef3c7}}
tr:target td{{background:#fde68a}}
</style></head><body>
<header><a href="/">&larr; docs-rag</a> &nbsp; {html.escape(rel_path)}</header>
<table>{"".join(rows)}</table>
</body></html>"""


def create_app(
    settings: Settings | None = None,
    pipeline: RAGPipeline | None = None,
    *,
    pipeline_factory: Callable[[Settings], RAGPipeline] | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    def get_pipeline() -> RAGPipeline:
        if app.state.pipeline is None:
            factory = app.state.pipeline_factory
            if factory is None:
                from docs_rag.bootstrap import build_pipeline

                factory = build_pipeline
            app.state.pipeline = factory(settings)
        return app.state.pipeline

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Build (or load) the index before serving so /health reports the chunk count and the
        # first /ask does not pay the indexing cost.
        get_pipeline()
        yield

    app = FastAPI(
        title="docs-rag",
        version=__version__,
        docs_url="/api-docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.pipeline = pipeline
    app.state.pipeline_factory = pipeline_factory
    app.state.rate_limiter = rate_limiter or RateLimiter(
        settings.rate_limit_per_minute, settings.rate_limit_burst
    )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health() -> dict[str, Any]:
        pipe = app.state.pipeline
        cap = pipe.cost_cap if pipe is not None else None
        return {
            "status": "ok",
            "version": __version__,
            "provider": settings.resolved_llm_provider(),
            "chunks": len(pipe.index.chunks) if pipe is not None else None,
            "daily_cost_cap_usd": settings.daily_cost_cap_usd,
            "spent_today_usd": round(cap.spent_today, 6) if cap is not None else None,
            "cache": pipe.cache.kind if pipe is not None and pipe.cache is not None else None,
        }

    @app.post("/ask", response_model=AskResponse)
    def ask(body: AskRequest, request: Request) -> AskResponse:
        ip = client_ip(request)
        allowed, retry_after = app.state.rate_limiter.allow(ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(max(1, int(retry_after + 0.999)))},
            )
        pipe = get_pipeline()
        try:
            result = pipe.ask(body.question, user_id=ip)
        except CostCapError as exc:
            raise HTTPException(
                status_code=429, detail=str(exc), headers={"Retry-After": "3600"}
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            log.exception("ask failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return AskResponse(
            answer=result.answer,
            citations=result.citations,
            refused=result.refused,
            refusal_reason=result.refusal_reason,
            trace_id=result.trace_id,
            latency_ms=round(result.latency_ms, 2),
            cost_usd=result.cost_usd,
            cache_hit=result.cache_hit,
            confidence=round(result.confidence, 4),
        )

    @app.get("/docs/{doc_path:path}", response_class=HTMLResponse)
    def serve_doc(doc_path: str, start: int | None = None, end: int | None = None) -> HTMLResponse:
        path = _resolve_doc(Path(settings.corpus_path), doc_path)
        text = path.read_text(encoding="utf-8", errors="replace")
        highlight = (start, end or start) if start else None
        return HTMLResponse(render_doc_html(doc_path, text, highlight))

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
        )

    return app


app = create_app()
