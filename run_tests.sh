#!/bin/bash
# Test Runner Script for Inventory Management System
# This script runs tests for all services

set -e

echo "🚀 Starting Inventory Management System Tests"
echo "=============================================="

# Install pytest globally for integration tests
echo "📦 Installing pytest globally..."
pip3 install pytest pytest-flask pytest-mock requests > /dev/null 2>&1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests for a service
run_service_tests() {
    local service_name=$1
    local service_dir=$2

    echo -e "\n${YELLOW}Testing ${service_name}...${NC}"
    echo "----------------------------------------"

    cd "$service_dir"

    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ requirements.txt not found in ${service_dir}${NC}"
        return 1
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "🐍 Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate

    # Install dependencies
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt > /dev/null 2>&1

    # Run tests
    echo "🧪 Running tests..."
    if python -m pytest -v --tb=short; then
        echo -e "${GREEN}✅ ${service_name} tests passed${NC}"
        deactivate
        return 0
    else
        echo -e "${RED}❌ ${service_name} tests failed${NC}"
        deactivate
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    echo -e "\n${YELLOW}🧪 Running Integration Tests...${NC}"
    echo "------------------------------"

    # Go back to root directory for integration tests
    cd "$SCRIPT_DIR"

    if python3 integration_tests.py; then
        echo -e "${GREEN}✅ Integration tests passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Integration tests failed${NC}"
        return 1
    fi
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Test services
FAILED_SERVICES=()

# Backend tests
if ! run_service_tests "Backend Service" "${SCRIPT_DIR}/backend"; then
    FAILED_SERVICES+=("Backend")
fi

# Alert service tests
if ! run_service_tests "Alert Service" "${SCRIPT_DIR}/alert-service"; then
    FAILED_SERVICES+=("Alert Service")
fi

# Reporting service tests
if ! run_service_tests "Reporting Service" "${SCRIPT_DIR}/reporting-service"; then
    FAILED_SERVICES+=("Reporting Service")
fi

# Integration tests
if ! run_integration_tests; then
    FAILED_SERVICES+=("Integration Tests")
fi

# Summary
echo -e "\n${YELLOW}Test Summary${NC}"
echo "=============="

if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo "✅ Ready for deployment"
    exit 0
else
    echo -e "${RED}❌ Some tests failed:${NC}"
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "${RED}  - ${service}${NC}"
    done
    echo -e "\n${YELLOW}Please fix the failing tests before deploying.${NC}"
    exit 1
fi