# Use a slim Python image
FROM python:3.11-slim-bookworm AS builder

# Copy uv binary from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set uv environment variables for optimal performance in Docker
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_MANAGED_PYTHON=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy dependency definition files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies before copying the application code.
# The `--frozen` flag guarantees reproducible builds, and `--no-install-project`
# skips installing the source code (which isn't copied yet).
RUN uv sync --frozen --no-install-project --extra orchestration --extra tracking

# Now copy the application code
COPY src/ src/
COPY scripts/ scripts/
COPY configs/ configs/
COPY Makefile .

# Sync again to install the project package itself
RUN uv sync --frozen --extra orchestration --extra tracking

# -------------------------
# Production Runner Stage
# -------------------------
FROM python:3.11-slim-bookworm

# Set Python behavior rules
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime system dependencies if needed (e.g. for ML/graph rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy the completely built application and virtual environment from the builder
COPY --from=builder /app /app

# By default, start a bash shell.
# On AWS ECS/Batch, you will override the command (CMD) in your Task Definition.
# Example ECS override: ["python", "-m", "src.cli", "run-pipeline", "--config", "configs/my_config.yml"]
CMD ["/bin/bash"]
