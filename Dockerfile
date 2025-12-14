FROM python:3.14.2-slim-trixie@sha256:2751cbe93751f0147bc1584be957c6dd4c5f977c3d4e0396b56456a9fd4ed137 AS base
COPY --from=ghcr.io/astral-sh/uv:0.9.17@sha256:5cb6b54d2bc3fe2eb9a8483db958a0b9eebf9edff68adedb369df8e7b98711a2 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN useradd -m user && \
    chown -R user:user /app

USER user

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1

RUN uv sync --dev --frozen --extra cpu

COPY src/ ./src/

# run linting and code quality checks
RUN basedpyright .
RUN ruff check --no-fix .
RUN ruff format --check .

# run tests (when available)

FROM base AS build

USER user

RUN uv sync --no-dev --frozen --extra cpu

FROM python:3.14.2-slim-trixie@sha256:2751cbe93751f0147bc1584be957c6dd4c5f977c3d4e0396b56456a9fd4ed137 AS production

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y \
      libgl1 \
      libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/.venv ./.venv
COPY src/ ./src/

RUN useradd -m user && \
    chown -R user:user /app

USER user

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "src/inference.py"]
