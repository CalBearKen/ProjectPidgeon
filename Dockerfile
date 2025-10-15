# Dockerfile for Pidgeon Protocol Components
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./
COPY pidgeon ./pidgeon
COPY config ./config
COPY examples ./examples

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 pidgeon && \
    chown -R pidgeon:pidgeon /app
USER pidgeon

# Default command (will be overridden by docker-compose)
CMD ["python", "-m", "pidgeon.planner"]

