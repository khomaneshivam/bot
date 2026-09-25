# Multi-stage Docker build for QuantAI Autonomous Trading System

# Stage 1: Build React 18 + Tailwind CSS Client
FROM node:20-alpine AS frontend-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci --silent
COPY client/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY bot/ ./bot/
COPY server/ ./server/
COPY shared/ ./shared/
COPY run.py .
# Environment variables injected at runtime via docker run --env-file or docker compose

# Copy compiled React frontend assets from builder stage
COPY --from=frontend-builder /app/client/dist ./client/dist
COPY client/public ./client/public

# Create data directory for SQLite trade ledger persistence
RUN mkdir -p /app/data

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8000

# Start Autonomous FastAPI Server
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
