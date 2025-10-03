FROM python:3.13.7@sha256:0c745292b7b34dcdd6050527907d78c39363dc45ad6afc6d107c454b93cebca1 AS base
COPY --from=ghcr.io/astral-sh/uv:0.8.22@sha256:9874eb7afe5ca16c363fe80b294fe700e460df29a55532bbfea234a0f12eddb1 /uv /uvx /bin/

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

FROM python:3.13.7-slim@sha256:5f55cdf0c5d9dc1a415637a5ccc4a9e18663ad203673173b8cda8f8dcacef689 AS production

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
