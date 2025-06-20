# Basic RAG System with NVIDIA NIM

A streamlined, production-ready RAG (Retrieval-Augmented Generation) system built with NVIDIA NIM microservices, featuring modular services architecture and Docker Compose deployment.

## Table of Contents

* [Overview](#overview)
* [Quick Start](#quick-start)
* [Architecture](#architecture)
* [Services](#services)
* [Configuration](#configuration)
* [Usage](#usage)
* [Troubleshooting](#troubleshooting)
* [License](#license)

## Overview

This repository provides a streamlined RAG system that leverages NVIDIA NIM microservices for local deployment. The system is designed with a modular services architecture, making it easy to deploy, scale, and maintain.

### Key Features

- **Local NIM Deployment**: Run NVIDIA NIM microservices locally for LLM inference and embeddings
- **Modular Architecture**: Separate services for chain server, RAG playground, and vector database
- **Docker Compose Deployment**: Simple one-command deployment with Docker Compose
- **LangChain Integration**: Built with LangChain for flexible RAG pipeline development
- **Milvus Vector Database**: High-performance vector storage and retrieval
- **Web UI**: Interactive playground for testing and using the RAG system

## Quick Start

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with Docker GPU support
- NVIDIA NGC API Key

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag_sys
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env file with your NGC API key and other settings
   ```

3. **Deploy the system**
   ```bash
   docker compose up -d --build
   ```

4. **Access the services**
   - RAG Playground UI: http://localhost:8090
   - Chain Server API: http://localhost:8081
   - Milvus Vector DB: http://localhost:19530

## Architecture

The system consists of the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  RAG Playground │    │   Chain Server  │    │ NVIDIA NIM LLM  │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   Inference     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Milvus Vector   │    │ NVIDIA NIM      │
                       │   Database      │◄──►│  Embeddings     │
                       └─────────────────┘    └─────────────────┘
```

## Services

### Chain Server
- **Purpose**: Core RAG logic and API endpoints
- **Technology**: FastAPI with LangChain
- **Port**: 8081
- **Features**: Document ingestion, retrieval, generation

### RAG Playground
- **Purpose**: Web-based user interface
- **Technology**: Streamlit
- **Port**: 8090
- **Features**: Interactive chat, document upload, configuration

### NVIDIA NIM Services
- **LLM Inference**: Meta Llama 3 8B Instruct (Port 8000)
- **Embeddings**: NVIDIA NV-EmbedQA-E5-V5 (Port 9080)
- **Features**: Local GPU-accelerated inference

### Vector Database
- **Technology**: Milvus with GPU acceleration
- **Port**: 19530
- **Features**: High-performance vector storage and similarity search

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# NVIDIA NGC API Key (required)
NGC_API_KEY=your_ngc_api_key_here

# Model cache directory
MODEL_DIRECTORY=/path/to/model/cache

# GPU configuration
VECTORSTORE_GPU_DEVICE_ID=0
EMBEDDING_MS_GPU_ID=0
INFERENCE_GPU_COUNT=1

# Model selection
APP_LLM_MODELNAME=meta/llama3-8b-instruct
APP_EMBEDDINGS_MODELNAME=nvidia/nv-embedqa-e5-v5
```

### Service Configuration

Each service can be configured through environment variables:
- **Chain Server**: Model endpoints, retrieval parameters, logging
- **RAG Playground**: UI settings, server connections
- **NIM Services**: Model selection, GPU allocation, caching

## Usage

### Document Upload
1. Access the RAG Playground at http://localhost:8090
2. Navigate to the "Knowledge Base" tab
3. Upload documents (PDF, TXT, MD supported)
4. Wait for processing and indexing

### Querying
1. Go to the "Chat" tab
2. Enable "Use Knowledge Base" for RAG queries
3. Ask questions about your uploaded documents
4. View responses with retrieved context

### API Access
Direct API access via Chain Server:
```bash
# Health check
curl http://localhost:8081/health

# Upload document
curl -X POST -F "file=@document.pdf" http://localhost:8081/documents

# Query with RAG
curl -X POST http://localhost:8081/generate \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Your question"}], "use_knowledge_base": true}'
```

## Troubleshooting

### Common Issues

1. **GPU Memory Issues**
   - Reduce `INFERENCE_GPU_COUNT` or use smaller models
   - Monitor GPU memory with `nvidia-smi`

2. **Model Download Failures**
   - Verify NGC API key is valid
   - Check internet connectivity
   - Ensure sufficient disk space in `MODEL_DIRECTORY`

3. **Service Startup Issues**
   - Check Docker logs: `docker compose logs <service-name>`
   - Verify all required environment variables are set
   - Ensure GPU drivers and Docker GPU support are installed

### Logs and Monitoring
```bash
# View all service logs
docker compose logs

# View specific service logs
docker compose logs chain-server
docker compose logs rag-playground

# Follow logs in real-time
docker compose logs -f
```

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

