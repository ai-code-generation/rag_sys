FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY . /app/
COPY embedding_server.py /app/embedding_server.py
RUN pip install --no-cache-dir -r requirements.txt
# Pre-download model
ARG MODEL_NAME=sentence-transformers/all-mpnet-base-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MODEL_NAME}')"

# Create user AFTER copying files
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app \
    && mkdir -p /home/app/.cache \
    && chown -R app:app /home/app/.cache

# ⭐ Verify file after chown


# Environment
ENV PYTHONPATH=/app
ENV TOKENIZERS_PARALLELISM=false
ENV MODEL_NAME=${MODEL_NAME}
ENV PORT=8000

EXPOSE 8000

# ⭐ Test file accessibility before CMD

CMD ["python", "embedding_server.py"]