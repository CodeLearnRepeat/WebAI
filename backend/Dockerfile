FROM python:3.11-slim

# Runtime env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    PORT=8080

# Minimal OS deps (libgomp for NumPy/OpenMP; curl for debugging/health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (caching best practice)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Optional: Pre-download default embedding model to reduce cold starts
# If you change the default model, update this line accordingly or remove it.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('Model cached')"

# Copy application code
COPY app ./app

# Cloud Run listens on $PORT (default 8080)
EXPOSE 8080

# Start FastAPI with Uvicorn (SSE-friendly single worker)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]