# VLA Inference API Platform - Production Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Build stage
FROM python:3.10-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# Install Python 3.10
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 vlaapi && \
    mkdir -p /app /models && \
    chown -R vlaapi:vlaapi /app /models

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/vlaapi/.local

# Copy application code
COPY --chown=vlaapi:vlaapi . .

# Set Python path
ENV PATH=/home/vlaapi/.local/bin:$PATH \
    PYTHONPATH=/app

# Switch to app user
USER vlaapi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["python3", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
