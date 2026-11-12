# syntax=docker/dockerfile:1
#
# Analysis image: the same Python, the same locked dependencies and the same code as the laptop
# and CI (D-015, D-131). It holds no data and no credentials: .dockerignore is an allowlist.
#
#   docker build -t sinac-truncation .
#   docker run --rm sinac-truncation pytest
#
# The tests marked `db` skip, because the image starts no database.

# The Python of .python-version, at the patch version the laptop ran when the image was written.
FROM python:3.12.14-slim-trixie

LABEL org.opencontainers.image.title="sinac-truncation" \
      org.opencontainers.image.source="https://github.com/martinruhle/sinac-prenatal-truncation"

# git: the tests of `publish` build a throwaway repository (tests/test_publish.py).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# The uv version the project is built with (pyproject.toml, [build-system]).
COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /bin/

# The environment lives outside /app, uses the image's Python and is first on PATH, so `pytest`
# and `python` resolve to it without `uv run`.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTEST_ADDOPTS="-p no:cacheprovider"

WORKDIR /app

# Dependencies first, from the lock file alone: this layer is rebuilt only when uv.lock changes,
# not on every change to the code. The dev group stays in, because the image runs the tests.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Then the code, and the project itself.
COPY src/ src/
COPY scripts/ scripts/
COPY sql/ sql/
COPY config/ config/
COPY tests/ tests/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# The code belongs to root and the image runs as a user that cannot change it.
RUN useradd --create-home --uid 1000 analyst
USER analyst

CMD ["python", "scripts/pipeline.py", "--help"]
