# RAG System Deployment Guide

## Quick Start (Local NIM Deployment)

For local deployment with NVIDIA NIM microservices:

1. **Prerequisites**:
   - NVIDIA GPU with Docker GPU support
   - NVIDIA Container Toolkit installed

2. **Get your NGC API Key**:
   - Visit [https://ngc.nvidia.com/](https://ngc.nvidia.com/)
   - Sign up/login and get your NGC API key

3. **Set your API keys**:
   ```bash
   export NGC_API_KEY="your-ngc-api-key-here"
   export NVIDIA_API_KEY="nvapi-your-key-here"  # Optional fallback
   ```

4. **Deploy the system**:
   ```bash
   docker compose --profile local-nim --profile milvus up -d --build
   ```

5. **Access the application**:
   - Open [http://localhost:8090](http://localhost:8090) for the RAG Playground
   - Upload documents and start chatting!

## Alternative: Cloud API Deployment

For setup using NVIDIA's hosted AI endpoints (no GPU required):

1. **Get NVIDIA API Key**: Visit [https://build.nvidia.com/](https://build.nvidia.com/)
2. **Set API key**: `export NVIDIA_API_KEY="nvapi-your-key-here"`
3. **Deploy**: `docker compose up -d --build` (without profiles)

## Configuration Options

### Environment Variables

The system uses a `.env` file for configuration. Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
# Edit .env with your API keys and preferences
```

#### For Local NIM Deployment:
- `NGC_API_KEY`: Your NGC API key from ngc.nvidia.com (REQUIRED)
- `MODEL_DIRECTORY`: Local directory for model caching (default: ./models)
- `APP_LLM_SERVERURL`: Local LLM endpoint (default: http://nemollm-inference:8000/v1)
- `APP_EMBEDDINGS_SERVERURL`: Local embedding endpoint (default: http://nemollm-embedding:8000/v1)

#### For Cloud API Deployment:
- `NVIDIA_API_KEY`: Your NVIDIA API key from build.nvidia.com (REQUIRED)
- `APP_LLM_SERVERURL`: Leave empty for cloud API
- `APP_EMBEDDINGS_SERVERURL`: Leave empty for cloud API

#### Database & Service Configuration:
- `APP_VECTORSTORE_URL`: Vector database endpoint (default: http://milvus:19530)
- `DOCKER_VOLUME_DIRECTORY`: Directory for persistent storage (default: ./volumes)
- `COLLECTION_NAME`: Vector store collection name (default: nvidia_api_catalog)

### Deployment Modes

#### 1. NVIDIA AI Endpoints (Recommended for getting started)
- No GPU required
- Uses NVIDIA's hosted models
- Requires only `NVIDIA_API_KEY`

#### 2. Local NIM Deployment
- Requires NVIDIA GPU
- Requires `NGC_API_KEY`
- Downloads and runs models locally

## Services

The system includes:

- **Vector Database**: Milvus for storing embeddings
- **Chain Server**: FastAPI server for RAG processing
- **RAG Playground**: Web UI for interaction
- **NIM Services**: NVIDIA Inference Microservices (optional for local deployment)

## Troubleshooting

### Common Issues:

1. **Missing API Key**: Set `NVIDIA_API_KEY` environment variable
2. **Port Conflicts**: Check if ports 8090, 8081, 19530 are available
3. **GPU Issues**: For local NIM, ensure NVIDIA Docker runtime is installed

### Logs:
```bash
# View all service logs
docker compose logs

# View specific service logs
docker compose logs chain-server
docker compose logs rag-playground
```

### Stop Services:
```bash
docker compose down
```

### Clean Reset:
```bash
docker compose down -v
docker system prune -f
```
