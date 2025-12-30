# Multi-stage Dockerfile for Finance Consolidator

# Stage 1: Build Svelte frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY backend/ ./backend/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/backend/static ./backend/static

# Create necessary directories
RUN mkdir -p /app/data/logs /app/data/cache /app/data/uploads /app/data/credentials

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/api/v1/health', timeout=2)"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV CONFIG_DIR=/app/config

# Start application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
