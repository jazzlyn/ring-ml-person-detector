FROM python:3.13@sha256:68d0775234842868248bfe185eece56e725d3cb195f511a21233d0f564dee501 AS base
COPY --from=ghcr.io/astral-sh/uv:0.8.5@sha256:9ac8566d708f42bae522b050004f75ebc7c344bc726d6d4e70f1d308b18c4471 /uv /uvx /bin/

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1

RUN uv sync --no-dev --frozen --extra cpu

ENV PATH="/app/.venv/bin:$PATH"


FROM base AS development

RUN uv sync --dev --frozen

COPY src/ ./src/

# run linting and code quality checks
RUN uv run ruff check .
RUN uv run ruff format --check .
RUN uv run basedpyright .
RUN uv run pylint src/

# run tests (when available)

FROM python:3.13-slim@sha256:6f79e7a10bb7d0b0a50534a70ebc78823f941fba26143ecd7e6c5dca9d7d7e8a AS production

RUN apt-get update && apt-get install --no-install-recommends -y \
      libgl1-mesa-glx \
      libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd --system --no-create-home user \
    && chown -R user /app

USER user

COPY --from=base /app ./
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "src/inference.py"]
