#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed."
        exit 1
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is required but not installed."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Setup Python virtual environment
setup_python() {
    print_header "Setting up Python Environment"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    pip install -r requirements-dev.txt
    
    print_success "Python environment ready"
}

# Setup Serverless Framework
setup_serverless() {
    print_header "Setting up Serverless Framework"
    
    # Install Serverless Framework and plugins
    npm install -g serverless
    npm install
    
    print_success "Serverless Framework ready"
}

# Start local DynamoDB
start_dynamodb() {
    print_header "Starting Local DynamoDB"
    
    # Check if DynamoDB container is already running
    if docker ps | grep -q "dynamodb-local"; then
        print_success "DynamoDB already running"
        return
    fi
    
    # Start DynamoDB container
    docker run -d -p 8000:8000 amazon/dynamodb-local
    
    print_success "DynamoDB started"
}

# Setup git hooks
setup_git_hooks() {
    print_header "Setting up Git Hooks"
    
    # Create pre-commit hook
    mkdir -p .git/hooks
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Activate virtual environment
source venv/bin/activate

# Run linting
make lint

# Run unit tests
make test-unit

echo "Pre-commit checks passed"
EOF
    
    chmod +x .git/hooks/pre-commit
    
    print_success "Git hooks configured"
}

# Make scripts executable
make_scripts_executable() {
    print_header "Making Scripts Executable"
    
    chmod +x scripts/*.sh
    chmod +x scripts/*.py
    
    print_success "Scripts are now executable"
}

# Main setup
main() {
    print_header "Starting Development Environment Setup"
    
    check_prerequisites
    setup_python
    setup_serverless
    start_dynamodb
    setup_git_hooks
    make_scripts_executable
    
    print_header "Setup Complete!"
    echo -e "\nTo activate the virtual environment, run:"
    echo -e "${GREEN}source venv/bin/activate${NC}"
    echo -e "\nTo start development, run:"
    echo -e "${GREEN}make dev${NC}"
}

# Run main function
main