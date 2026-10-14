# `llm-evalops` is a path dependency (../llm-evalops) and lives outside this build context, so
# pass it as a named context:
#   docker build --build-context llm-evalops=../llm-evalops -t docs-rag:latest .
# ---- build stage: resolve and install dependencies with uv -------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# `../llm-evalops` relative to /app is /llm-evalops.
COPY --from=llm-evalops pyproject.toml README.md /llm-evalops/
COPY --from=llm-evalops src /llm-evalops/src

# Install third-party dependencies first so this layer is cached across source changes.
# --no-editable installs llm-evalops into the virtualenv, so the runtime stage does not need
# its sources.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---- runtime stage: slim image with only the virtualenv and runtime files --------------
FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --chown=app:app data/corpus ./data/corpus
COPY --chown=app:app pricing.json ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    CORPUS_PATH=/app/data/corpus \
    INDEX_PATH=/app/data/index/index.npz \
    TRACE_PATH=/app/traces/spans.jsonl \
    PRICING_PATH=/app/pricing.json

RUN mkdir -p /app/data/index /app/traces && chown -R app:app /app/data /app/traces
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

CMD ["uvicorn", "docs_rag.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
