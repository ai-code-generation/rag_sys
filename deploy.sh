#!/bin/bash

# Custom Basic RAG Modular Deployment Script
echo "🚀 Starting Custom Basic RAG Modular Deployment"

# Check if NVIDIA_API_KEY is set
if [ -z "$NVIDIA_API_KEY" ]; then
    echo "❌ Error: NVIDIA_API_KEY environment variable is not set"
    echo "Please set your NVIDIA API key:"
    echo "export NVIDIA_API_KEY=\"nvapi-your-key-here\""
    echo ""
    echo "Get your free API key from: https://build.nvidia.com/explore/discover"
    exit 1
fi

echo "✅ NVIDIA_API_KEY is set"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

echo "✅ Docker is running"

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
    echo "✅ Created .env file. You can customize it if needed."
fi

echo "🐳 Starting modular RAG services..."
$COMPOSE_CMD up -d --build

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
    echo ""
    echo "📖 Usage:"
    echo "  1. Open http://localhost:8090 in your browser"
    echo "  2. Go to 'Knowledge Base' tab to upload documents"
    echo "  3. Go to 'Chat' tab to ask questions about your documents"
    echo ""
    echo "🔧 Management Commands:"
    echo "  - View logs:        $COMPOSE_CMD logs -f"
    echo "  - Stop services:    $COMPOSE_CMD down"
    echo "  - Restart service:  $COMPOSE_CMD restart <service-name>"
    echo "  - Scale service:    $COMPOSE_CMD up -d --scale <service-name>=<count>"
    echo ""
    echo "📚 Documentation:"
    echo "  - Main README:      README.md"
    echo "  - API Docs:         docs/api.md"
    echo "  - Chain Server:     services/chain-server/README.md"
    echo "  - RAG Playground:   services/rag-playground/README.md"
    echo ""
    echo "🐛 Troubleshooting:"
    echo "  - Check service logs: $COMPOSE_CMD logs <service-name>"
    echo "  - Restart all:        $COMPOSE_CMD restart"
    echo "  - Clean restart:      $COMPOSE_CMD down && $COMPOSE_CMD up -d --build"
else
    echo "❌ Deployment failed. Check the logs with:"
    echo "$COMPOSE_CMD logs"
    exit 1
fi
