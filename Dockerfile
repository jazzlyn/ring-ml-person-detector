FROM python:3.13@sha256:5f69d22a88dd4cc4ee1576def19aef48c8faa1b566054c44291183831cbad13b AS base

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 655 /install.sh && /install.sh && rm /install.sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

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

FROM python:3.13-slim@sha256:f2fdaec50160418e0c2867ba3e254755edd067171725886d5d303fd7057bbf81 AS production

RUN apt-get update && apt-get install --no-install-recommends -y \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd --system --no-create-home user \
    && chown -R user /app

USER user

COPY --from=base /app ./
COPY src/ ./src/
COPY config/ ./config/

ENV YOLO_CONFIG_DIR="/app/yolo"
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "src/inference.py"]
