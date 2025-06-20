@echo off
echo 🚀 Starting Custom Basic RAG Modular Deployment

REM Check if NVIDIA_API_KEY is set
if "%NVIDIA_API_KEY%"=="" (
    echo ❌ Error: NVIDIA_API_KEY environment variable is not set
    echo Please set your NVIDIA API key:
    echo set NVIDIA_API_KEY=nvapi-your-key-here
    echo.
    echo Get your free API key from: https://build.nvidia.com/explore/discover
    pause
    exit /b 1
)

echo ✅ NVIDIA_API_KEY is set

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not running
    echo Please start Docker and try again
    pause
    exit /b 1
)

echo ✅ Docker is running

REM Check if docker-compose or docker compose is available
docker-compose version >nul 2>&1
if not errorlevel 1 (
    set COMPOSE_CMD=docker-compose
    goto :compose_found
)

docker compose version >nul 2>&1
if not errorlevel 1 (
    set COMPOSE_CMD=docker compose
    goto :compose_found
)

echo ❌ Error: Neither docker-compose nor 'docker compose' is available
echo Please install Docker Compose and try again
pause
exit /b 1

:compose_found
echo ✅ Docker Compose is available

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env >nul
    echo ✅ Created .env file. You can customize it if needed.
)

echo 🐳 Starting modular RAG services...
%COMPOSE_CMD% up -d --build

if errorlevel 0 (
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
    echo.
    echo 📖 Usage:
    echo   1. Open http://localhost:8090 in your browser
    echo   2. Go to 'Knowledge Base' tab to upload documents
    echo   3. Go to 'Chat' tab to ask questions about your documents
    echo.
    echo 🔧 Management Commands:
    echo   - View logs:        %COMPOSE_CMD% logs -f
    echo   - Stop services:    %COMPOSE_CMD% down
    echo   - Restart service:  %COMPOSE_CMD% restart ^<service-name^>
    echo   - Scale service:    %COMPOSE_CMD% up -d --scale ^<service-name^>=^<count^>
    echo.
    echo 📚 Documentation:
    echo   - Main README:      README.md
    echo   - API Docs:         docs\api.md
    echo   - Chain Server:     services\chain-server\README.md
    echo   - RAG Playground:   services\rag-playground\README.md
    echo.
    echo 🐛 Troubleshooting:
    echo   - Check service logs: %COMPOSE_CMD% logs ^<service-name^>
    echo   - Restart all:        %COMPOSE_CMD% restart
    echo   - Clean restart:      %COMPOSE_CMD% down ^&^& %COMPOSE_CMD% up -d --build
) else (
    echo ❌ Deployment failed. Check the logs with:
    echo %COMPOSE_CMD% logs
    pause
    exit /b 1
)

pause
