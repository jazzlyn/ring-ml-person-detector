FROM python:3.14.2-slim-trixie@sha256:3955a7dd66ccf92b68d0232f7f86d892eaf75255511dc7e98961bdc990dc6c9b AS base
COPY --from=ghcr.io/astral-sh/uv:0.9.24@sha256:816fdce3387ed2142e37d2e56e1b1b97ccc1ea87731ba199dc8a25c04e4997c5 /uv /uvx /bin/

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

FROM python:3.14.2-slim-trixie@sha256:3955a7dd66ccf92b68d0232f7f86d892eaf75255511dc7e98961bdc990dc6c9b AS production

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
