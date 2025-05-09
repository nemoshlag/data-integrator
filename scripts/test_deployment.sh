#!/bin/bash
set -e

# Default values
STAGE=${STAGE:-dev}
REGION=${AWS_REGION:-eu-west-1}
STACK_NAME="hospital-data-integrator-${STAGE}"

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
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is required but not installed."
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Get stack outputs
get_stack_outputs() {
    print_header "Getting Stack Information"
    
    # Get stack outputs
    STACK_OUTPUT=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    # Extract endpoints
    API_URL=$(echo $STACK_OUTPUT | jq -r '.[] | select(.OutputKey=="ServiceEndpoint") | .OutputValue')
    WEBSOCKET_URL=$(echo $STACK_OUTPUT | jq -r '.[] | select(.OutputKey=="WebSocketEndpoint") | .OutputValue')
    S3_BUCKET=$(echo $STACK_OUTPUT | jq -r '.[] | select(.OutputKey=="UploadBucket") | .OutputValue')
    
    if [ -z "$API_URL" ] || [ -z "$WEBSOCKET_URL" ]; then
        print_error "Failed to get API endpoints from stack outputs"
        exit 1
    fi
    
    print_success "Retrieved stack outputs"
}

# Setup Python virtual environment and install dependencies
setup_python() {
    print_header "Setting up Python Environment"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install -r requirements.txt
    pip install requests websockets
    
    print_success "Python environment ready"
}

# Run deployment tests
run_tests() {
    print_header "Running Deployment Tests"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run test script
    python scripts/test_deployment.py \
        --api-url ${API_URL} \
        --websocket-url ${WEBSOCKET_URL} \
        --stage ${STAGE} \
        --s3-bucket ${S3_BUCKET}
    
    if [ $? -eq 0 ]; then
        print_success "All tests passed"
    else
        print_error "Some tests failed"
        exit 1
    fi
}

# Cleanup
cleanup() {
    print_header "Cleaning Up"
    
    # Deactivate virtual environment
    deactivate 2>/dev/null || true
    
    print_success "Cleanup complete"
}

# Main execution
main() {
    # Handle errors
    trap cleanup EXIT
    
    print_header "Starting Deployment Tests for Stage: ${STAGE}"
    
    check_prerequisites
    get_stack_outputs
    setup_python
    run_tests
    
    print_header "Testing Complete"
}

# Run main function
main