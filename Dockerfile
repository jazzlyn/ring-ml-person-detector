FROM python:3.14.0@sha256:934873f1360893d07afe0d25b99af46640e916a5900f1677fb86e41f73920253 AS base
COPY --from=ghcr.io/astral-sh/uv:0.9.7@sha256:ba4857bf2a068e9bc0e64eed8563b065908a4cd6bfb66b531a9c424c8e25e142 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1

RUN uv sync --dev --frozen --extra cpu

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"

# run linting and code quality checks
RUN basedpyright .
RUN ruff check --no-fix .
RUN ruff format --check .

# run tests (when available)

RUN uv sync --no-dev --frozen --extra cpu

FROM python:3.14.0-slim@sha256:4ed33101ee7ec299041cc41dd268dae17031184be94384b1ce7936dc4e5dead3 AS production

RUN apt-get update && apt-get install --no-install-recommends -y \
      libgl1 \
      libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd --system --no-create-home user && \
    chown -R user /app

USER user

COPY --from=base /app/.venv ./.venv
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV TORCH_HOME=/app/.cache/torch

EXPOSE 8000

CMD ["python", "src/inference.py"]
