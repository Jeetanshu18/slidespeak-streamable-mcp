# ---- Stage 1: Build with uv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy instead of linking since cache mount is not available
ENV UV_LINK_MODE=copy

# Copy lockfile and settings first (to leverage Docker layer caching)
COPY uv.lock pyproject.toml ./

# Install dependencies only (not project code yet)
RUN uv sync --frozen --no-install-project --no-dev --no-editable

# Copy the rest of the project
COPY . /app

# Install the project itself
RUN uv sync --frozen --no-dev --no-editable

# Ensure /root/.local exists (some images require this)
RUN mkdir -p /root/.local


# ---- Stage 2: Runtime image ----
FROM python:3.12-slim-bookworm

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv and installed packages
COPY --from=uv /root/.local /root/.local
COPY --from=uv /app/.venv /app/.venv

# Copy application code
COPY --from=uv /app/src /app/src
COPY --from=uv /app/pyproject.toml /app/pyproject.toml
COPY --from=uv /app/.env /app/.env

# Add venv executables to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["python", "/app/src/server.py"]
