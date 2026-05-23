FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt

# Copy application files
COPY scripts/embed_docs.py .
COPY backend ./backend
COPY docs ./docs

# Create db directory for ChromaDB
RUN mkdir -p ./db

# Embed documents on startup
RUN python embed_docs.py || true

EXPOSE 8000

# Run FastAPI with Uvicorn
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
