<!--
  SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
  SPDX-License-Identifier: Apache-2.0
-->

# Basic RAG Using LangChain

## Example Features

This example deploys a basic RAG pipeline for chat Q&A and serves inferencing from an NVIDIA API Catalog endpoint.
You do not need a GPU on your machine to run this example.

| Model                    | Embedding                | Framework | Vector Database | File Types   |
| ------------------------ | ------------------------ | --------- | --------------- | ------------ |
| meta/llama3-70b-instruct | nvidia/nv-embedqa-e5-v5 | LangChain | Milvus          | TXT, PDF, MD |

## Quick Start

### Option 1: Easy Configuration (Recommended)
```bash
# Run the configuration script
./configure.sh

# Follow the prompts to choose deployment mode
# Script will configure .env and show deployment commands
```

### Option 2: Manual Configuration

**For Local NIM Deployment (requires GPU):**
1. Get your NGC API Key from [https://ngc.nvidia.com/](https://ngc.nvidia.com/)
2. Set your API key: `export NGC_API_KEY="your-ngc-api-key-here"`
3. Deploy: `docker compose up -d --build`

**For Cloud API Deployment (no GPU required):**
1. Get your NVIDIA API Key from [https://build.nvidia.com/](https://build.nvidia.com/)
2. Set your API key: `export NVIDIA_API_KEY="nvapi-your-key-here"`
3. Configure for cloud mode (set `APP_LLM_SERVERURL=""` in .env)
4. Deploy: `docker compose up -d --build`

**Access the application**: Open [http://localhost:8090](http://localhost:8090)

For detailed deployment options and troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md).

   *Example Output*

   ```output
    ✔ Network nvidia-rag           Created
    ✔ Container rag-playground     Started
    ✔ Container milvus-minio       Started
    ✔ Container chain-server       Started
    ✔ Container milvus-etcd        Started
    ✔ Container milvus-standalone  Started
   ```

1. Confirm the containers are running:

   ```console
   docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"
   ```

   *Example Output*

   ```output
   CONTAINER ID   NAMES               STATUS
   39a8524829da   rag-playground      Up 2 minutes
   bfbd0193dbd2   chain-server        Up 2 minutes
   ec02ff3cc58b   milvus-standalone   Up 3 minutes
   6969cf5b4342   milvus-minio        Up 3 minutes (healthy)
   57a068d62fbb   milvus-etcd         Up 3 minutes (healthy)
   ```

1. Open a web browser and access <http://localhost:8090> to use the RAG Playground.

   You can upload documents and interact with the RAG system through the web interface.

## Architecture

This RAG system uses a modular services architecture with the following components:

- **Vector Database** (`services/vectordb/`): Milvus for storing and retrieving embeddings
- **NIM Microservices** (`services/nim-ms/`): NVIDIA NIM for LLM and embedding models
- **Chain Server** (`services/chain_server/`): FastAPI server handling RAG processing
- **RAG Playground** (`services/rag_playground/`): Web UI for interaction

## Next Steps

- Upload documents through the web interface
- Experiment with different queries and prompts
- Stop the containers by running `docker compose down`
