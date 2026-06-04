FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install uv — the fast Python package manager
# Pinned version for reproducible builds
RUN pip install --no-cache-dir uv==0.4.10

# Install dependencies first — this layer is cached until pyproject.toml changes.
# Copying only pyproject.toml before the source means a source-only change
# does not trigger a full dependency reinstall.
COPY pyproject.toml .
RUN uv sync --all-extras

# Copy the rest of the source
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Development: --reload watches for file changes (volume-mounted source)
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
