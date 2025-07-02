FROM python:3.12@sha256:77a36ff63e657d8ec7cd4e86e452f4cd23b6c92811696b0735226fbc0660a5b8 AS base
COPY --from=ghcr.io/astral-sh/uv:0.7.17@sha256:68a26194ea8da0dbb014e8ae1d8ab08a469ee3ba0f4e2ac07b8bb66c0f8185c1 /uv /uvx /bin/

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

FROM python:3.12-slim@sha256:4600f71648e110b005bf7bca92dbb335e549e6b27f2e83fceee5e11b3e1a4d01 AS production

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
