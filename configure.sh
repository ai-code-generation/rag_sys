#!/bin/bash

# Configuration helper script for Custom Basic RAG
echo "🔧 Custom Basic RAG Configuration Helper"
echo ""

print_help() {
    echo "Usage: $0 [cloud|local-nim]"
    echo ""
    echo "Commands:"
    echo "  cloud      Configure for NVIDIA AI Endpoints (cloud)"
    echo "  local-nim  Configure for local NVIDIA NIM services"
    echo "  help       Show this help message"
    echo ""
    echo "This script will update your .env file with the appropriate configuration."
}

configure_cloud() {
    echo "🌐 Configuring for NVIDIA AI Endpoints (cloud)..."
    
    # Create .env from template if it doesn't exist
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "✅ Created .env file from template"
    fi
    
    # Update configuration for cloud
    sed -i 's/APP_LLM_MODELENGINE=.*/APP_LLM_MODELENGINE=nvidia-ai-endpoints/' .env
    sed -i 's/APP_EMBEDDINGS_MODELENGINE=.*/APP_EMBEDDINGS_MODELENGINE=nvidia-ai-endpoints/' .env
    sed -i 's/APP_LLM_SERVERURL=.*/APP_LLM_SERVERURL=/' .env
    sed -i 's/APP_EMBEDDINGS_SERVERURL=.*/APP_EMBEDDINGS_SERVERURL=/' .env
    
    echo "✅ Configuration updated for cloud deployment"
    echo ""
    echo "📝 Next steps:"
    echo "1. Set your NVIDIA API key: export NVIDIA_API_KEY=\"nvapi-your-key-here\""
    echo "2. Deploy with: docker compose up -d --build"
    echo ""
    echo "🔗 Get your free API key: https://build.nvidia.com/explore/discover"
}

configure_local_nim() {
    echo "🏠 Configuring for local NVIDIA NIM services..."
    
    # Create .env from template if it doesn't exist
    if [ ! -f .env ]; then
        cp .env.example .env
        echo "✅ Created .env file from template"
    fi
    
    # Update configuration for local NIM
    sed -i 's/APP_LLM_MODELENGINE=.*/APP_LLM_MODELENGINE=local-nim/' .env
    sed -i 's/APP_EMBEDDINGS_MODELENGINE=.*/APP_EMBEDDINGS_MODELENGINE=local-nim/' .env
    sed -i 's|APP_LLM_SERVERURL=.*|APP_LLM_SERVERURL=http://nemollm-inference:8000/v1|' .env
    sed -i 's|APP_EMBEDDINGS_SERVERURL=.*|APP_EMBEDDINGS_SERVERURL=http://nemollm-embedding:8000/v1|' .env
    sed -i 's/NGC_API_KEY=.*/NGC_API_KEY=your-ngc-api-key-here/' .env
    sed -i 's|MODEL_DIRECTORY=.*|MODEL_DIRECTORY=./models|' .env
    
    # Create models directory
    mkdir -p models
    echo "✅ Created models directory"
    
    echo "✅ Configuration updated for local NIM deployment"
    echo ""
    echo "📝 Next steps:"
    echo "1. Set your NGC API key: export NGC_API_KEY=\"your-ngc-api-key-here\""
    echo "2. Set your NVIDIA API key: export NVIDIA_API_KEY=\"nvapi-your-key-here\""
    echo "3. Deploy with: ./deploy-local-nim.sh"
    echo ""
    echo "🔗 Get your NGC API key: https://ngc.nvidia.com/"
    echo "⚠️  Requirements: NVIDIA GPU with 16GB+ VRAM, NVIDIA Docker runtime"
}

# Main command handling
case "${1:-help}" in
    cloud)
        configure_cloud
        ;;
    local-nim)
        configure_local_nim
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        print_help
        exit 1
        ;;
esac
