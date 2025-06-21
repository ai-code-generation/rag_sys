#!/bin/bash

# RAG System Configuration Script
# This script helps configure the system for different deployment modes

set -e

echo "🚀 RAG System Configuration"
echo "=========================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "📋 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file"
fi

echo ""
echo "Choose deployment mode:"
echo "1) Local NIM Deployment (requires GPU + NGC API key)"
echo "2) Cloud API Deployment (requires NVIDIA API key)"
echo ""
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo "🏠 Configuring for Local NIM Deployment"
        echo "======================================="
        
        # Prompt for NGC API key
        read -p "Enter your NGC API key: " ngc_key
        if [ -z "$ngc_key" ]; then
            echo "❌ NGC API key is required for local deployment"
            exit 1
        fi
        
        # Update .env for local deployment
        sed -i "s/NGC_API_KEY=.*/NGC_API_KEY=$ngc_key/" .env
        sed -i "s/APP_LLM_MODELNAME=.*/APP_LLM_MODELNAME=meta\/llama3-8b-instruct/" .env
        sed -i "s/APP_LLM_SERVERURL=.*/APP_LLM_SERVERURL=http:\/\/nemollm-inference:8000\/v1/" .env
        sed -i "s/APP_EMBEDDINGS_SERVERURL=.*/APP_EMBEDDINGS_SERVERURL=http:\/\/nemollm-embedding:8000\/v1/" .env
        
        echo "✅ Configured for local NIM deployment"
        echo ""
        echo "🚀 To deploy, run:"
        echo "docker compose up -d --build"
        ;;
        
    2)
        echo ""
        echo "☁️  Configuring for Cloud API Deployment"
        echo "========================================"
        
        # Prompt for NVIDIA API key
        read -p "Enter your NVIDIA API key: " nvidia_key
        if [ -z "$nvidia_key" ]; then
            echo "❌ NVIDIA API key is required for cloud deployment"
            exit 1
        fi
        
        # Update .env for cloud deployment
        sed -i "s/NVIDIA_API_KEY=.*/NVIDIA_API_KEY=$nvidia_key/" .env
        sed -i "s/APP_LLM_MODELNAME=.*/APP_LLM_MODELNAME=meta\/llama3-70b-instruct/" .env
        sed -i "s/APP_LLM_SERVERURL=.*/APP_LLM_SERVERURL=/" .env
        sed -i "s/APP_EMBEDDINGS_SERVERURL=.*/APP_EMBEDDINGS_SERVERURL=/" .env
        
        echo "✅ Configured for cloud API deployment"
        echo ""
        echo "🚀 To deploy, run:"
        echo "docker compose up -d --build"
        ;;
        
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "📝 Configuration complete!"
echo "🌐 Access the application at: http://localhost:8090"
echo ""
echo "📚 For more details, see DEPLOYMENT.md"
