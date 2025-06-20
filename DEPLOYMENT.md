# RAG System Deployment Guide

## Quick Start (Using NVIDIA AI Endpoints)

For the fastest setup using NVIDIA's hosted AI endpoints:

1. **Get your NVIDIA API Key**:
   - Visit [https://build.nvidia.com/](https://build.nvidia.com/)
   - Sign up/login and get your API key

2. **Set your API key**:
   ```bash
   export NVIDIA_API_KEY="nvapi-your-key-here"
   ```

3. **Deploy the system**:
   ```bash
   docker compose up -d --build
   ```

4. **Access the application**:
   - Open [http://localhost:8090](http://localhost:8090) for the RAG Playground
   - Upload documents and start chatting!

## Configuration Options

### Environment Variables

The system uses a `.env` file for configuration. Key variables:

#### Required for NVIDIA AI Endpoints:
- `NVIDIA_API_KEY`: Your NVIDIA API key from build.nvidia.com

#### Optional for Local NIM Deployment:
- `NGC_API_KEY`: Your NGC API key from ngc.nvidia.com
- `MODEL_DIRECTORY`: Local directory for model storage (leave empty for default)
- `USERID`: User ID for container permissions (leave empty for default)

#### Database Configuration:
- `DOCKER_VOLUME_DIRECTORY`: Directory for persistent storage (default: ./volumes)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: password)
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
