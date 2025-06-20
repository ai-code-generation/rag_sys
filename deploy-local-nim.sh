#!/bin/bash

# Local NIM Deployment Script for Custom Basic RAG
echo "🚀 Starting Custom Basic RAG with Local NIM Services"

# Check if NGC_API_KEY is set
if [ -z "$NGC_API_KEY" ]; then
    echo "❌ Error: NGC_API_KEY environment variable is not set"
    echo "Please set your NGC API key:"
    echo "export NGC_API_KEY=\"your-ngc-api-key-here\""
    echo ""
    echo "Get your NGC API key from: https://ngc.nvidia.com/"
    echo "You need this to download the NIM container images."
    exit 1
fi

echo "✅ NGC_API_KEY is set"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

echo "✅ Docker is running"

# Check for NVIDIA Docker runtime
if ! docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi > /dev/null 2>&1; then
    echo "❌ Error: NVIDIA Docker runtime not available"
    echo "Please install nvidia-docker2 and restart Docker daemon"
    echo "See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi

echo "✅ NVIDIA Docker runtime is available"

# Check if docker-compose or docker compose is available
if command -v docker-compose > /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
elif docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ Error: Neither docker-compose nor 'docker compose' is available"
    echo "Please install Docker Compose and try again"
    exit 1
fi

echo "✅ Docker Compose is available"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please update NGC_API_KEY and other settings as needed."
fi

# Create models directory if it doesn't exist
if [ ! -d models ]; then
    echo "📁 Creating models directory..."
    mkdir -p models
    echo "✅ Created models directory"
fi

echo "🐳 Starting RAG services with local NIM..."
$COMPOSE_CMD --profile local-nim up -d --build

# Check if services started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "📊 Services Status:"
    $COMPOSE_CMD ps
    echo ""
    echo "🌐 Access Points:"
    echo "  - RAG Playground UI: http://localhost:8090"
    echo "  - Chain Server API:  http://localhost:8081"
    echo "  - API Documentation: http://localhost:8081/docs"
    echo "  - LLM NIM Service:   http://localhost:8000"
    echo "  - Embedding NIM:     http://localhost:9080"
    echo ""
    echo "⚠️  Note: NIM services may take several minutes to download models and start"
    echo "   Monitor progress with: $COMPOSE_CMD logs -f nemollm-inference nemollm-embedding"
    echo ""
    echo "📖 Usage:"
    echo "  1. Wait for NIM services to be ready (check logs)"
    echo "  2. Open http://localhost:8090 in your browser"
    echo "  3. Go to 'Knowledge Base' tab to upload documents"
    echo "  4. Go to 'Chat' tab to ask questions about your documents"
    echo ""
    echo "🔧 Management Commands:"
    echo "  - View logs:        $COMPOSE_CMD logs -f"
    echo "  - Stop services:    $COMPOSE_CMD --profile local-nim down"
    echo "  - Restart service:  $COMPOSE_CMD restart <service-name>"
    echo ""
    echo "🐛 Troubleshooting:"
    echo "  - Check NIM logs:     $COMPOSE_CMD logs nemollm-inference nemollm-embedding"
    echo "  - Check GPU usage:    nvidia-smi"
    echo "  - Clean restart:      $COMPOSE_CMD --profile local-nim down && $COMPOSE_CMD --profile local-nim up -d --build"
else
    echo "❌ Deployment failed. Check the logs with:"
    echo "$COMPOSE_CMD logs"
    exit 1
fi
