# Stage 1: Build Frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend

# Copy package files first for caching
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ .
# Create output directory explicitly to avoid issues with outDir being outside root
RUN mkdir -p /app/backend/static
RUN npm run build

# Stage 2: Runtime
FROM python:3.10-slim
WORKDIR /app

# Install basic system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ backend/
COPY src/ src/
COPY scripts/ scripts/
# Copy default config (can be overridden by volume)
COPY config/ config/

# Create necessary data directories
RUN mkdir -p data/uploads data/logs data/cache data/temp

# Copy built frontend assets from builder stage
# vite.config.js outputs to ../backend/static, which effectively is /app/backend/static in the builder
COPY --from=frontend-build /app/backend/static backend/static

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose the port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
