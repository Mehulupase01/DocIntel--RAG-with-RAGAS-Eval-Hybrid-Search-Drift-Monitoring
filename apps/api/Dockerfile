FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.5.21
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_PYTHON_REFRESH=quiet \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app/src

WORKDIR /app

COPY --from=builder --chown=app:app /app /app
RUN mkdir -p /app/.model_cache /app/artifacts \
    && chown -R app:app /app

USER app
VOLUME ["/app/.model_cache", "/app/artifacts"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://localhost:8000/api/v1/health/liveness', timeout=5)" || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn docintel.main:app --host 0.0.0.0 --port 8000"]
