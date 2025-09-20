FROM python:3.13.7@sha256:2deb0891ec3f643b1d342f04cc22154e6b6a76b41044791b537093fae00b6884 AS base
COPY --from=ghcr.io/astral-sh/uv:0.8.19@sha256:0ca07117081b2c6a8dd813d2badacf76dceecaf8b8a41d51b5d715024ffef7d8 /uv /uvx /bin/

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

FROM python:3.13.7-slim@sha256:58c30f5bfaa718b5803a53393190b9c68bd517c44c6c94c1b6c8c172bcfad040 AS production

RUN apt-get update && apt-get install --no-install-recommends -y \
      libgl1-mesa-glx \
      libglib2.0-0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd --system --no-create-home user && \
    chown -R user /app

USER user

COPY --from=base /app ./
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "src/inference.py"]
