#!/bin/bash

# Simple Deployment Script for HuggingFace Embedding Server
# Direct Flask server access (no Nginx)

set -e

echo "🚀 Deploying HuggingFace Embedding Server (Simple)"
echo "================================================="

# Default values
MODEL_NAME="sentence-transformers/all-mpnet-base-v2"
PORT=8000
BIND_IP="0.0.0.0"
DETACHED=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --bind-ip)
            BIND_IP="$2"
            shift 2
            ;;
        --foreground)
            DETACHED=false
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --model MODEL      HuggingFace model name"
            echo "  --port PORT        Server port (default: 8000)"
            echo "  --bind-ip IP       Bind IP (default: 0.0.0.0 for external access)"
            echo "  --foreground       Run in foreground (don't detach)"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Simple deployment"
            echo "  $0 --model all-MiniLM-L6-v2 --port 8001"
            echo "  $0 --bind-ip 192.168.1.100"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "📦 Model: $MODEL_NAME"
echo "🌐 Bind IP: $BIND_IP"
echo "🔌 Port: $PORT"
echo "🏃 Mode: $([ "$DETACHED" = true ] && echo "detached" || echo "foreground")"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

# Create simple environment file
echo "📝 Creating environment..."
cat > .env.simple << EOF
MODEL_NAME=$MODEL_NAME
PORT=$PORT
BIND_IP=$BIND_IP
WORKERS=1
MEMORY_LIMIT=2G
MEMORY_RESERVATION=1G
FLASK_HOST=$BIND_IP
LOG_LEVEL=INFO
EOF

# Create simple docker-compose file
echo "📝 Creating docker-compose configuration..."
cat > docker-compose.simple.yml << EOF
version: '3.8'

services:
  embedding-server:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        MODEL_NAME: \${MODEL_NAME:-sentence-transformers/all-mpnet-base-v2}
    container_name: hf-embedding-server-simple
    restart: unless-stopped
    ports:
      - "\${BIND_IP:-0.0.0.0}:\${PORT:-8000}:8000"
    environment:
      - MODEL_NAME=\${MODEL_NAME:-sentence-transformers/all-mpnet-base-v2}
      - PORT=8000
      - WORKERS=\${WORKERS:-1}
      - TOKENIZERS_PARALLELISM=false
      - FLASK_HOST=\${FLASK_HOST:-0.0.0.0}
    volumes:
      - ./:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: \${MEMORY_LIMIT:-2G}
        reservations:
          memory: \${MEMORY_RESERVATION:-1G}

volumes:
  embedding_cache:
    driver: local
EOF

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.simple.yml --env-file .env.simple down 2>/dev/null || true

# Build and start
echo "🔨 Building and starting container..."
if [ "$DETACHED" = true ]; then
    docker-compose -f docker-compose.simple.yml --env-file .env.simple up -d --build
else
    docker-compose -f docker-compose.simple.yml --env-file .env.simple up --build
fi

if [ "$DETACHED" = true ]; then
    # Wait for service to start
    echo "⏳ Waiting for service to start..."
    sleep 15

    # Check service health
    echo "🔍 Checking service health..."
    CHECK_URL="http://$BIND_IP:$PORT/health"
    
    # Health check with retries
    for i in {1..12}; do
        if curl -s "$CHECK_URL" > /dev/null 2>&1; then
            echo "✅ Service is healthy!"
            break
        else
            if [ $i -eq 12 ]; then
                echo "❌ Service health check failed after 60 seconds"
                echo "📋 Container logs:"
                docker-compose -f docker-compose.simple.yml --env-file .env.simple logs --tail=20
                exit 1
            fi
            echo "⏳ Waiting for service... (attempt $i/12)"
            sleep 5
        fi
    done

    # Show deployment info
    echo ""
    echo "🎉 Simple Deployment Completed!"
    echo "=" * 40
    echo "📊 Service Information:"
    echo "  Model: $MODEL_NAME"
    echo "  URL: http://$BIND_IP:$PORT"
    echo "  Health: http://$BIND_IP:$PORT/health"
    echo "  Embeddings: http://$BIND_IP:$PORT/v1/embeddings"
    echo "  Models: http://$BIND_IP:$PORT/v1/models"
    echo ""
    echo "📋 Container Status:"
    docker-compose -f docker-compose.simple.yml --env-file .env.simple ps
    echo ""
    echo "🧪 Test the service:"
    echo "  curl $CHECK_URL"
    echo "  ./test_public_ip.sh --ip $BIND_IP --port $PORT"
    echo ""
    echo "🛑 Stop the service:"
    echo "  docker-compose -f docker-compose.simple.yml --env-file .env.simple down"
    echo ""
    echo "📊 View logs:"
    echo "  docker-compose -f docker-compose.simple.yml --env-file .env.simple logs -f"
    echo ""
    echo "🔧 Integration with RAG system:"
    echo "  APP_EMBEDDINGS_SERVERURL=\"http://$BIND_IP:$PORT/v1\""
fi
