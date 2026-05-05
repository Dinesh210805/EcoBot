# ── Stage 1: dependency builder ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for sentence-transformers and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# Pre-download embedding model so the image works offline
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"


# ── Stage 2: runtime image ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local
# Copy cached model
COPY --from=builder /root/.cache /root/.cache

# Non-root user for security
RUN useradd -m -u 1001 ecobot && \
    mkdir -p /app/data /app/embeddings /app/tmp/uploads && \
    chown -R ecobot:ecobot /app

USER ecobot

# Copy application code
COPY --chown=ecobot:ecobot backend/ ./backend/
COPY --chown=ecobot:ecobot scripts/ ./scripts/
COPY --chown=ecobot:ecobot data/ ./data/

# Environment defaults (override via docker run -e or .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    CLASSIFIER_MODE=ollama \
    SQLITE_DB_PATH=/app/data/ecobot.db \
    CHROMA_DB_PATH=/app/embeddings/chroma_db \
    UPLOAD_DIR=/app/tmp/uploads \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()"

# Init DB then start server
CMD ["sh", "-c", "python -m scripts.init_db && uvicorn backend.main:app --host $API_HOST --port $API_PORT --workers 2"]
