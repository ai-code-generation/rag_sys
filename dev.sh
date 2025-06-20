#!/bin/bash

# Development helper script for Custom Basic RAG Modular

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_help() {
    echo "Custom Basic RAG Development Helper"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services in development mode"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  logs [service]  Show logs (optionally for specific service)"
    echo "  build           Build all services"
    echo "  clean           Clean up containers and volumes"
    echo "  test            Run tests (if available)"
    echo "  shell [service] Open shell in service container"
    echo "  status          Show service status"
    echo "  help            Show this help message"
    echo ""
    echo "Services:"
    echo "  - chain-server"
    echo "  - rag-playground"
    echo "  - milvus"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs chain-server        # Show chain-server logs"
    echo "  $0 shell chain-server       # Open shell in chain-server"
    echo "  $0 restart rag-playground   # Restart just the playground"
}

check_requirements() {
    if [ -z "$NVIDIA_API_KEY" ]; then
        echo -e "${RED}❌ NVIDIA_API_KEY not set${NC}"
        echo "Please set your NVIDIA API key:"
        echo "export NVIDIA_API_KEY=\"nvapi-your-key-here\""
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found${NC}"
        exit 1
    fi

    # Check for docker-compose or docker compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ Docker Compose not found${NC}"
        exit 1
    fi
}

start_services() {
    echo -e "${BLUE}🚀 Starting development environment...${NC}"
    check_requirements
    
    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
    fi
    
    $COMPOSE_CMD up -d --build
    echo -e "${GREEN}✅ Services started${NC}"
    show_status
}

stop_services() {
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}✅ Services stopped${NC}"
}

restart_services() {
    local service=$1
    if [ -n "$service" ]; then
        echo -e "${BLUE}🔄 Restarting $service...${NC}"
        $COMPOSE_CMD restart "$service"
    else
        echo -e "${BLUE}🔄 Restarting all services...${NC}"
        $COMPOSE_CMD restart
    fi
    echo -e "${GREEN}✅ Restart complete${NC}"
}

show_logs() {
    local service=$1
    if [ -n "$service" ]; then
        $COMPOSE_CMD logs -f "$service"
    else
        $COMPOSE_CMD logs -f
    fi
}

build_services() {
    echo -e "${BLUE}🔨 Building services...${NC}"
    $COMPOSE_CMD build
    echo -e "${GREEN}✅ Build complete${NC}"
}

clean_environment() {
    echo -e "${YELLOW}🧹 Cleaning up environment...${NC}"
    $COMPOSE_CMD down -v --remove-orphans
    docker system prune -f
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

open_shell() {
    local service=$1
    if [ -z "$service" ]; then
        echo -e "${RED}❌ Please specify a service${NC}"
        echo "Available services: chain-server, rag-playground"
        exit 1
    fi
    
    echo -e "${BLUE}🐚 Opening shell in $service...${NC}"
    $COMPOSE_CMD exec "$service" /bin/bash
}

show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    $COMPOSE_CMD ps
    echo ""
    echo -e "${BLUE}🌐 Access Points:${NC}"
    echo "  - RAG Playground: http://localhost:8090"
    echo "  - Chain Server:   http://localhost:8081"
    echo "  - API Docs:       http://localhost:8081/docs"
}

run_tests() {
    echo -e "${BLUE}🧪 Running tests...${NC}"
    # Add test commands here when tests are implemented
    echo -e "${YELLOW}⚠️  Tests not yet implemented${NC}"
}

# Main command handling
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        check_requirements
        stop_services
        ;;
    restart)
        check_requirements
        restart_services "$2"
        ;;
    logs)
        check_requirements
        show_logs "$2"
        ;;
    build)
        check_requirements
        build_services
        ;;
    clean)
        check_requirements
        clean_environment
        ;;
    test)
        check_requirements
        run_tests
        ;;
    shell)
        check_requirements
        open_shell "$2"
        ;;
    status)
        check_requirements
        show_status
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac
