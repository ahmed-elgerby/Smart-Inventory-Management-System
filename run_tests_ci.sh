#!/bin/bash
# CI Test Runner - Optimized for Jenkins
# Runs all tests with Jenkins-compatible output formats
# Usage: ./run_tests_ci.sh [--integration-only] [--unit-only] [--verbose]

set -e

# Source CI environment file
if [ -f .env.ci ]; then
    export $(cat .env.ci | grep -v '#' | xargs)
fi

# Color codes (disabled in CI)
if [ -z "$NO_COLOR" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Logging function
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Parse arguments
INTEGRATION_ONLY=false
UNIT_ONLY=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --integration-only)
            INTEGRATION_ONLY=true
            shift
            ;;
        --unit-only)
            UNIT_ONLY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create output directories
mkdir -p "${TEST_RESULTS_DIR}" "${COVERAGE_DIR}" "${LOGS_DIR}"

log_info "📦 Starting CI Test Suite"
log_info "=========================="

# Track test results
FAILED_TESTS=()
TOTAL_TESTS=0
PASSED_TESTS=0

# Run unit tests
run_unit_tests() {
    local service_name=$1
    local service_dir=$2
    
    if [ "$INTEGRATION_ONLY" = true ]; then
        return 0
    fi
    
    log_info "🧪 Running ${service_name} unit tests..."
    
    cd "$service_dir" || return 1
    
    if [ ! -f "requirements.txt" ]; then
        log_warning "requirements.txt not found in ${service_dir}"
        cd - > /dev/null
        return 1
    fi
    
    # Install dependencies
    log_info "  📦 Installing dependencies..."
    pip install -q -r requirements.txt > "${LOGS_DIR}/${service_name}-install.log" 2>&1 || {
        log_error "Failed to install dependencies for ${service_name}"
        cat "${LOGS_DIR}/${service_name}-install.log"
        cd - > /dev/null
        return 1
    }
    
    # Run tests with JUnit XML output
    local test_file="${service_dir}/test_${service_name}.py"
    if [ "$VERBOSE" = true ]; then
        pytest_args="-v --tb=short"
    else
        pytest_args="-v --tb=short"
    fi
    
    if python -m pytest \
        $pytest_args \
        --junit-xml="../${TEST_RESULTS_DIR}/${service_name}-results.xml" \
        --cov=. \
        --cov-report=xml:"../${COVERAGE_DIR}/${service_name}-coverage.xml" \
        --cov-report=html:"../${COVERAGE_DIR}/${service_name}" \
        --cov-report=term > "${LOGS_DIR}/${service_name}-test.log" 2>&1; then
        
        log_success "${service_name} tests passed"
        ((PASSED_TESTS++))
    else
        log_error "${service_name} tests failed"
        if [ "$VERBOSE" = true ]; then
            cat "${LOGS_DIR}/${service_name}-test.log"
        fi
        FAILED_TESTS+=("${service_name}")
        return 1
    fi
    
    ((TOTAL_TESTS++))
    cd - > /dev/null
    return 0
}

# Run integration tests
run_integration_tests() {
    if [ "$UNIT_ONLY" = true ]; then
        return 0
    fi
    
    log_info "🔗 Running integration tests..."
    
    # Install dependencies
    pip install -q requests > "${LOGS_DIR}/integration-install.log" 2>&1 || {
        log_error "Failed to install dependencies for integration tests"
        return 1
    }
    
    if python3 integration_tests.py > "${LOGS_DIR}/integration-test.log" 2>&1; then
        log_success "Integration tests passed"
        ((PASSED_TESTS++))
    else
        log_error "Integration tests failed"
        if [ "$VERBOSE" = true ]; then
            cat "${LOGS_DIR}/integration-test.log"
        fi
        FAILED_TESTS+=("Integration Tests")
        return 1
    fi
    
    ((TOTAL_TESTS++))
    return 0
}

# Main execution
log_info "Installing global dependencies..."
pip install -q pytest pytest-cov pytest-flask pytest-mock requests > /dev/null 2>&1 || {
    log_warning "Some packages may already be installed"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Run unit tests
run_unit_tests "backend" "backend"
run_unit_tests "alert_service" "alert-service"
run_unit_tests "reporting_service" "reporting-service"

# Run integration tests
run_integration_tests

# Generate summary report
log_info "📊 Generating test reports..."

# Create summary file for Jenkins
{
    echo "Test Execution Summary"
    echo "====================="
    echo "Timestamp: $(date -Iseconds)"
    echo "Total Tests: $((TOTAL_TESTS + FAILED_TESTS[@]))"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: ${#FAILED_TESTS[@]}"
    echo ""
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "Failed Tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
    fi
    
    echo ""
    echo "Log Files:"
    ls -1 "${LOGS_DIR}/"
    echo ""
    echo "JUnit Reports:"
    ls -1 "${TEST_RESULTS_DIR}/"*.xml 2>/dev/null || echo "  No JUnit reports generated"
    echo ""
    echo "Coverage Reports:"
    ls -1 "${COVERAGE_DIR}/"*.xml 2>/dev/null || echo "  No coverage reports generated"
} | tee "${TEST_RESULTS_DIR}/summary.txt"

# Exit status
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    log_success "✅ All tests passed!"
    exit 0
else
    log_error "❌ Some tests failed:"
    for test in "${FAILED_TESTS[@]}"; do
        echo "    - $test"
    done
    exit 1
fi
