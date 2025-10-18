FROM python:3.14.0@sha256:e3a6ccbe44d9cbfa4f107f238a0e95fa70e0d084e87689222e951d062ac89854 AS base
COPY --from=ghcr.io/astral-sh/uv:0.9.4@sha256:35aca64ac15f61941da93e92ebfb22220359e95056e6a827f4aef2235c4d353f /uv /uvx /bin/

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

FROM python:3.14.0-slim@sha256:5cfac249393fa6c7ebacaf0027a1e127026745e603908b226baa784c52b9d99b AS production

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
