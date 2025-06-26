# Dockerfile
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install setuptools and poetry
RUN pip install --no-cache-dir 'setuptools<81' poetry

# Set working directory
WORKDIR /app

# Copy poetry files first (for better caching)
COPY pyproject.toml poetry.lock* ./

# Configure poetry and install only external dependencies (no local packages)
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Create luigi state directory
RUN mkdir -p /luigi/state

# Default command (can be overridden in docker-compose)
CMD ["poetry", "run", "luigid", "--port", "8082"]