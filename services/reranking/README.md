# Custom Reranking Service

A custom reranking service that implements the NVIDIA NIM reranking API interface using sentence-transformers cross-encoder models.

## Features

- **NVIDIA NIM Compatible API**: Implements the same `/v1/ranking` endpoint as NVIDIA NIM reranking service
- **Lightweight**: Uses efficient cross-encoder models from sentence-transformers
- **Flexible**: Easy to swap different reranking models
- **Production Ready**: Includes health checks, error handling, and logging

## API Endpoints

### POST /v1/ranking
Rerank passages based on relevance to a query.

**Request:**
```json
{
  "model": "custom-reranker",
  "query": {"text": "which way should i go?"},
  "passages": [
    {"text": "passage 1 text"},
    {"text": "passage 2 text"}
  ],
  "truncate": "END"
}
```

**Response:**
```json
{
  "rankings": [
    {"index": 0, "logit": -1.2421875},
    {"index": 1, "logit": -3.029296875}
  ]
}
```

### GET /health
Basic health check endpoint.

### GET /v1/health/ready
NIM-compatible health ready check.

## Configuration

The service uses the `cross-encoder/ms-marco-MiniLM-L-6-v2` model by default. You can modify the model in `app.py` by changing the `model_name` variable in the `load_reranker_model()` function.

## Supported Models

Any cross-encoder model from sentence-transformers can be used:
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (default, lightweight)
- `cross-encoder/ms-marco-MiniLM-L-12-v2` (better accuracy)
- `cross-encoder/ms-marco-electra-base` (high accuracy)

## Deployment

The service runs on port 8000 internally and is exposed on port 8765 when deployed with Docker Compose.

## Limits

- Maximum 512 passages per request
- Token limits depend on the underlying model (typically ~512 tokens)
- Supports truncation strategies: "NONE" (error on overflow) or "END" (truncate excess tokens)
