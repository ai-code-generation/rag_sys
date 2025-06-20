# Services Directory

This directory contains all the modular services that make up the RAG system.

## Services Overview

### chain_server/
The chain server service that handles RAG processing and API endpoints.

**Key Files:**
- `server.py` - FastAPI server implementation
- `Dockerfile` - Container build configuration
- `requirements.txt` - Python dependencies

### nim-ms/
NVIDIA NIM (NVIDIA Inference Microservices) service for LLM and embedding models.

**Key Files:**
- `docker-compose.yaml` - NIM microservices configuration

### vectordb/
Vector database service (Milvus, pgvector, etc.) for storing and retrieving embeddings.

**Key Files:**
- `docker-compose.yaml` - Vector database configuration

### rag_playground/
Web UI for interacting with the RAG system.

**Key Files:**
- `Dockerfile` - Container build configuration
- `requirements.txt` - Python dependencies

## Usage

These services are automatically included when you run the main docker-compose.yaml from the root directory:

```bash
# From the root directory
docker-compose up -d
```

Each service can also be deployed independently if needed by navigating to the specific service directory and running its docker-compose file.
