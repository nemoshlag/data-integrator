#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DYNAMODB_PORT=8000
SERVERLESS_PORT=3000
API_PORT=4000

print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    dependencies=("docker" "python3" "pip" "serverless")
    missing_deps=()
    
    for dep in "${dependencies[@]}"; do
        if ! command -v $dep &> /dev/null; then
            missing_deps+=($dep)
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    print_success "All dependencies are installed"
}

start_dynamodb() {
    print_header "Starting DynamoDB Local"
    
    if docker ps | grep -q "dynamodb-local"; then
        print_success "DynamoDB is already running"
    else
        docker run -d -p $DYNAMODB_PORT:$DYNAMODB_PORT amazon/dynamodb-local
        print_success "DynamoDB started on port $DYNAMODB_PORT"
    fi
}

stop_dynamodb() {
    print_header "Stopping DynamoDB Local"
    
    if docker ps | grep -q "dynamodb-local"; then
        docker stop $(docker ps -q --filter ancestor=amazon/dynamodb-local)
        print_success "DynamoDB stopped"
    else
        print_success "DynamoDB is not running"
    fi
}

init_tables() {
    print_header "Initializing DynamoDB Tables"
    
    python3 scripts/init_local_tables.py
    print_success "Tables initialized"
}

start_serverless() {
    print_header "Starting Serverless Offline"
    
    serverless offline start \
        --httpPort $API_PORT \
        --lambdaPort $SERVERLESS_PORT &
    
    print_success "Serverless started on port $API_PORT"
}

start_dev() {
    check_dependencies
    start_dynamodb
    sleep 2  # Wait for DynamoDB to start
    init_tables
    start_serverless
    
    print_header "Development Environment Ready"
    echo -e "Services running:"
    echo -e "- DynamoDB: http://localhost:$DYNAMODB_PORT"
    echo -e "- API: http://localhost:$API_PORT"
    echo -e "\nUse 'make logs' to view Lambda logs"
    echo -e "Use 'make stop-local' to stop all services"
}

stop_dev() {
    print_header "Stopping Development Environment"
    
    # Stop serverless offline
    pkill -f "serverless offline" || true
    
    # Stop DynamoDB
    stop_dynamodb
    
    print_success "All services stopped"
}

show_status() {
    print_header "Development Environment Status"
    
    # Check DynamoDB
    if docker ps | grep -q "dynamodb-local"; then
        print_success "DynamoDB is running on port $DYNAMODB_PORT"
    else
        print_error "DynamoDB is not running"
    fi
    
    # Check Serverless
    if pgrep -f "serverless offline" > /dev/null; then
        print_success "Serverless is running on port $API_PORT"
    else
        print_error "Serverless is not running"
    fi
}

case "$1" in
    "start")
        start_dev
        ;;
    "stop")
        stop_dev
        ;;
    "restart")
        stop_dev
        sleep 2
        start_dev
        ;;
    "status")
        show_status
        ;;
    "init-tables")
        init_tables
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|init-tables}"
        exit 1
        ;;
esac