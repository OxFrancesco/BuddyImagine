# syntax=docker/dockerfile:1

# BuddyImagine Telegram Bot
# Multi-stage build for optimized production image

# =============================================================================
# Stage 1: Builder - Install dependencies using uv
# =============================================================================
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (better layer caching)
# Copy only dependency files for caching
COPY pyproject.toml uv.lock ./

# Sync dependencies (without dev dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.12-slim AS runtime

# Create non-root user for security
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home botuser

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder --chown=botuser:botuser /app/.venv /app/.venv

# Copy application code
COPY --chown=botuser:botuser main.py bot.py agent.py handlers.py ./
COPY --chown=botuser:botuser services/ ./services/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER botuser

# Health check - verify Python environment
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import aiogram; print('healthy')" || exit 1

# Default command
CMD ["python", "main.py"]
