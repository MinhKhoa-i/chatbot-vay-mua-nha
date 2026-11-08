FROM ghcr.io/astral-sh/uv:0.13.1 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/srv/ai_service/.venv/bin:$PATH" \
    TIKTOKEN_CACHE_DIR=/srv/tiktoken-cache

WORKDIR /srv/ai_service

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Cache the tokenizer at build time rather than downloading it on worker startup.
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN groupadd --system app && useradd --system --gid app app
USER app

CMD ["python", "-m", "app.infrastructure.jobs.worker"]
