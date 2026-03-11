FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev packages)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI server via uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
