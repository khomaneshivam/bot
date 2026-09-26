# Multi-stage Docker build for QuantAI Autonomous Trading System
# Stage 1: Build React 18 + Tailwind CSS Client
FROM node:20-alpine AS frontend-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci --silent
COPY client/ ./
RUN npm run build

# Stage 2: Hardened Python Backend Runtime
FROM python:3.11-slim
WORKDIR /app

# Install security updates and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user
RUN groupadd -g 1000 tradingbot && \
    useradd -u 1000 -g tradingbot -m -s /bin/bash tradingbot

# Copy python dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY bot/ ./bot/
COPY server/ ./server/
COPY shared/ ./shared/
COPY run.py .

# Copy compiled React frontend assets from builder stage
COPY --from=frontend-builder /app/client/dist ./client/dist
COPY client/public ./client/public

# Create data directory with permissions for non-root user
RUN mkdir -p /app/data && chown -R tradingbot:tradingbot /app

USER tradingbot

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8000
ENV ENVIRONMENT=production

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/metrics || exit 1

STOPSIGNAL SIGTERM

CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
