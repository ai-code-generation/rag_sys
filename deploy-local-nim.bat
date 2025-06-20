@echo off
setlocal enabledelayedexpansion

echo 🚀 Starting Custom Basic RAG with Local NIM Services

REM Check if NGC_API_KEY is set
if "%NGC_API_KEY%"=="" (
    echo ❌ Error: NGC_API_KEY environment variable is not set
    echo Please set your NGC API key:
    echo set NGC_API_KEY=your-ngc-api-key-here
    echo.
    echo Get your NGC API key from: https://ngc.nvidia.com/
    echo You need this to download the NIM container images.
    exit /b 1
)

echo ✅ NGC_API_KEY is set

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not running
    echo Please start Docker and try again
    exit /b 1
)

echo ✅ Docker is running

REM Check for NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: NVIDIA Docker runtime not available
    echo Please install nvidia-docker2 and restart Docker daemon
    echo See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
    exit /b 1
)

echo ✅ NVIDIA Docker runtime is available

REM Check if docker-compose or docker compose is available
docker-compose version >nul 2>&1
if not errorlevel 1 (
    set COMPOSE_CMD=docker-compose
) else (
    docker compose version >nul 2>&1
    if not errorlevel 1 (
        set COMPOSE_CMD=docker compose
    ) else (
        echo ❌ Error: Neither docker-compose nor 'docker compose' is available
        echo Please install Docker Compose and try again
        exit /b 1
    )
)

echo ✅ Docker Compose is available

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env >nul
    echo ✅ Created .env file. Please update NGC_API_KEY and other settings as needed.
)

REM Create models directory if it doesn't exist
if not exist models (
    echo 📁 Creating models directory...
    mkdir models
    echo ✅ Created models directory
)

echo 🐳 Starting RAG services with local NIM...
%COMPOSE_CMD% --profile local-nim up -d --build

if errorlevel 1 (
    echo ❌ Deployment failed. Check the logs with:
    echo %COMPOSE_CMD% logs
    exit /b 1
)

echo.
echo 🎉 Deployment successful!
echo.
echo 📊 Services Status:
%COMPOSE_CMD% ps
echo.
echo 🌐 Access Points:
echo   - RAG Playground UI: http://localhost:8090
echo   - Chain Server API:  http://localhost:8081
echo   - API Documentation: http://localhost:8081/docs
echo   - LLM NIM Service:   http://localhost:8000
echo   - Embedding NIM:     http://localhost:9080
echo.
echo ⚠️  Note: NIM services may take several minutes to download models and start
echo    Monitor progress with: %COMPOSE_CMD% logs -f nemollm-inference nemollm-embedding
echo.
echo 📖 Usage:
echo   1. Wait for NIM services to be ready (check logs)
echo   2. Open http://localhost:8090 in your browser
echo   3. Go to 'Knowledge Base' tab to upload documents
echo   4. Go to 'Chat' tab to ask questions about your documents
echo.
echo 🔧 Management Commands:
echo   - View logs:        %COMPOSE_CMD% logs -f
echo   - Stop services:    %COMPOSE_CMD% --profile local-nim down
echo   - Restart service:  %COMPOSE_CMD% restart ^<service-name^>
echo.
echo 🐛 Troubleshooting:
echo   - Check NIM logs:     %COMPOSE_CMD% logs nemollm-inference nemollm-embedding
echo   - Check GPU usage:    nvidia-smi
echo   - Clean restart:      %COMPOSE_CMD% --profile local-nim down ^&^& %COMPOSE_CMD% --profile local-nim up -d --build
