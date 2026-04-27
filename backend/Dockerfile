# Build stage
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev packages)
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY . .

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
