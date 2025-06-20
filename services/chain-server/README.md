# Chain Server Service

The Chain Server is the core backend service that handles RAG (Retrieval Augmented Generation) operations, document ingestion, and LLM interactions.

## Overview

This service provides a FastAPI-based REST API that:
- Ingests documents into a vector database
- Performs similarity search on document embeddings
- Generates responses using LLM with or without RAG
- Manages document lifecycle (upload, search, delete)

## Architecture

```
src/
├── server.py              # FastAPI application and endpoints
├── base.py                # Base classes for chain implementations
├── configuration.py       # Configuration management
├── tracing.py             # Observability and tracing
├── utils.py               # Utility functions for vector stores, LLMs, etc.
└── chains/
    └── basic_rag.py       # Basic RAG chain implementation
```

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Document Management
- `POST /documents` - Upload and ingest documents
- `GET /documents` - List ingested documents
- `DELETE /documents` - Delete specific documents

### Generation
- `POST /generate` - Generate responses with optional RAG
- `POST /search` - Search for relevant documents

## Configuration

The service is configured through environment variables:

### Vector Database
- `APP_VECTORSTORE_URL` - Vector database URL (default: http://milvus:19530)
- `APP_VECTORSTORE_NAME` - Vector database type (default: milvus)
- `COLLECTION_NAME` - Collection name for embeddings

### LLM Configuration
- `APP_LLM_MODELNAME` - LLM model name
- `APP_LLM_MODELENGINE` - LLM engine (nvidia-ai-endpoints)
- `APP_LLM_SERVERURL` - Custom LLM server URL (optional)

### Embedding Configuration
- `APP_EMBEDDINGS_MODELNAME` - Embedding model name
- `APP_EMBEDDINGS_MODELENGINE` - Embedding engine
- `APP_EMBEDDINGS_SERVERURL` - Custom embedding server URL (optional)

### Text Processing
- `APP_TEXTSPLITTER_MODELNAME` - Text splitter model
- `APP_TEXTSPLITTER_CHUNKSIZE` - Chunk size for text splitting
- `APP_TEXTSPLITTER_CHUNKOVERLAP` - Overlap between chunks

### Retrieval
- `APP_RETRIEVER_TOPK` - Number of documents to retrieve
- `APP_RETRIEVER_SCORETHRESHOLD` - Similarity score threshold

## Supported File Types

- `.txt` - Plain text files
- `.pdf` - PDF documents
- `.md` - Markdown files

## Development

### Building the Service
```bash
docker build -t chain-server .
```

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export NVIDIA_API_KEY="your-api-key"
export APP_VECTORSTORE_URL="http://localhost:19530"

# Run the server
uvicorn src.server:app --host 0.0.0.0 --port 8081
```

### Adding New Chain Implementations

1. Create a new file in `src/chains/`
2. Implement a class that inherits from `BaseExample`
3. Implement required methods: `ingest_docs`, `rag_chain`, `llm_chain`
4. The server will automatically discover and load your implementation

## Dependencies

Key dependencies include:
- FastAPI - Web framework
- LangChain - LLM orchestration
- Sentence Transformers - Text embeddings
- PyMilvus - Vector database client
- NVIDIA AI Endpoints - LLM and embedding APIs
