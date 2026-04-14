# Backend Dockerfile
# Multi-stage build for smaller production image

FROM python:3.11-slim AS base

# Install system dependencies for PDF processing + OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/papers /app/data/exports

# Non-root user for security
RUN useradd -r -s /bin/false paperlens && \
    chown -R paperlens:paperlens /app/data

USER paperlens

EXPOSE 8000

# FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
