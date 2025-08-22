FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Ensure /root/.local exists
RUN mkdir -p /root/.local

FROM python:3.12-slim-bookworm

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=uv /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv


COPY --from=uv --chown=app:app /app/src /app/src
COPY --from=uv --chown=app:app /app/pyproject.toml /app/pyproject.toml
COPY --from=uv --chown=app:app /app/.env /app/.env
# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENV HOST=0.0.0.0
ENV PORT=5001

EXPOSE 5001

# when running the container, add --db-path and a bind mount to the host's db file
#ENTRYPOINT ["sendgrid-mcp"]
ENTRYPOINT ["python", "/app/src/server.py"]
