#!/bin/bash

# Simple Monitoring Script for HuggingFace Embedding Server

echo "📊 HuggingFace Embedding Server Monitor (Simple)"
echo "==============================================="

# Function to check service status
check_status() {
    echo "🔍 Service Status"
    echo "-" * 20
    
    if docker ps | grep -q "hf-embedding-server-simple"; then
        echo "✅ Container is running"
        docker ps --filter "name=hf-embedding-server-simple" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "❌ Container is not running"
        return 1
    fi
    echo ""
}

# Function to check health
check_health() {
    echo "🏥 Health Check"
    echo "-" * 15
    
    # Try to find the port from running container
    local port=$(docker port hf-embedding-server-simple 8000 2>/dev/null | cut -d: -f2)
    
    if [ -z "$port" ]; then
        port=8000
    fi
    
    if curl -s "http://localhost:$port/health" > /dev/null; then
        echo "✅ Service healthy on port $port"
        curl -s "http://localhost:$port/health" | jq . 2>/dev/null || curl -s "http://localhost:$port/health"
        return 0
    else
        echo "❌ Service not responding on port $port"
        return 1
    fi
    echo ""
}

# Function to show resource usage
show_resources() {
    echo "💻 Resource Usage"
    echo "-" * 17
    
    if docker ps | grep -q "hf-embedding-server-simple"; then
        echo "📊 Container Stats:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" hf-embedding-server-simple
    else
        echo "❌ Container not running"
    fi
    echo ""
}

# Function to show logs
show_logs() {
    local lines=${1:-20}
    echo "📋 Recent Logs (last $lines lines)"
    echo "-" * 30
    
    if docker ps | grep -q "hf-embedding-server-simple"; then
        docker logs --tail=$lines hf-embedding-server-simple
    else
        echo "❌ Container not running"
    fi
    echo ""
}

# Function to test performance
test_performance() {
    echo "⚡ Performance Test"
    echo "-" * 18
    
    # Find the port
    local port=$(docker port hf-embedding-server-simple 8000 2>/dev/null | cut -d: -f2)
    
    if [ -z "$port" ]; then
        port=8000
    fi
    
    echo "Testing embedding generation speed on port $port..."
    
    local start_time=$(date +%s.%N)
    local response=$(curl -s -X POST "http://localhost:$port/v1/embeddings" \
        -H "Content-Type: application/json" \
        -d '{"input": "This is a performance test"}')
    local end_time=$(date +%s.%N)
    
    if echo "$response" | grep -q "embedding"; then
        local duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")
        echo "✅ Embedding generated in ${duration}s"
        
        local dimensions=$(echo "$response" | jq '.data[0].embedding | length' 2>/dev/null || echo "N/A")
        echo "📊 Dimensions: $dimensions"
    else
        echo "❌ Performance test failed"
        echo "Response: $response"
    fi
    echo ""
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status      Show service status"
    echo "  health      Check service health"
    echo "  resources   Show resource usage"
    echo "  logs [N]    Show last N log lines (default: 20)"
    echo "  perf        Run performance test"
    echo "  all         Run all checks"
    echo "  watch       Continuous monitoring (every 30s)"
    echo "  help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 logs 50"
    echo "  $0 watch"
}

# Function for continuous monitoring
watch_mode() {
    echo "👀 Continuous Monitoring (Press Ctrl+C to stop)"
    echo "=" * 50
    
    while true; do
        clear
        echo "📊 HuggingFace Embedding Server Monitor - $(date)"
        echo "=" * 60
        
        check_status
        check_health
        show_resources
        test_performance
        
        echo "⏰ Next update in 30 seconds... (Ctrl+C to stop)"
        sleep 30
    done
}

# Main script logic
case "${1:-all}" in
    "status")
        check_status
        ;;
    "health")
        check_health
        ;;
    "resources")
        show_resources
        ;;
    "logs")
        show_logs "${2:-20}"
        ;;
    "perf")
        test_performance
        ;;
    "all")
        check_status
        check_health
        show_resources
        test_performance
        ;;
    "watch")
        watch_mode
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
