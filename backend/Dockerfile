FROM python:3.11-slim

# Runtime env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    PORT=8080 \
    PYTHONPATH=/app

# Minimal OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps first
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Optional: cache default ST model to reduce cold start
RUN python -c "import sys; sys.path.append('/app'); exec('try:\\n from sentence_transformers import SentenceTransformer\\n SentenceTransformer(\\\"sentence-transformers/all-MiniLM-L6-v2\\\")\\n print(\\\"Model cached\\\")\\nexcept Exception as e:\\n print(\\\"Model caching failed:\\\", str(e))')" || true


# Copy code
COPY app ./app

# Fail fast during build if imports are broken (prints full traceback)
EXPOSE 8080

# More verbose logs to surface issues
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level debug"]