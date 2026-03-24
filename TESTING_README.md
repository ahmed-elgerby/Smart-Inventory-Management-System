# Testing Guide for Inventory Management System

This document describes the testing setup and how to run tests for the Inventory Management System.

## Overview

The system includes comprehensive tests for all three microservices:
- **Backend Service**: Main API with authentication, items, users, locations
- **Alert Service**: Alert generation and management
- **Reporting Service**: Analytics and reporting endpoints

## Test Structure

### Backend Service Tests (`backend/test_backend.py`)
- Authentication (login, token validation)
- CRUD operations for items, users, locations
- Analytics and metrics endpoints
- Authorization and permission checks

### Alert Service Tests (`alert-service/test_alert_service.py`)
- Alert creation and resolution logic
- Automatic alert generation based on stock levels
- API endpoints for alert management

### Reporting Service Tests (`reporting-service/test_reporting_service.py`)
- Report generation (inventory summary, alerts detail, activity log)
- Data integrity and calculation validation
- Comprehensive system reports

### Integration Tests (`integration_tests.py`)
- End-to-end service communication testing
- Cross-service data flow validation
- Alert generation from backend inventory changes
- Reporting service data consistency checks
- Full system workflow testing

## Running Tests

### Option 1: Run All Tests (Recommended)
```bash
# Make the script executable (first time only)
chmod +x run_tests.sh

# Run all tests across all services
./run_tests.sh
```

### Option 2: Run Tests for Individual Services
```bash
# Backend tests
cd backend
pip install -r requirements.txt
python -m pytest -v

# Alert service tests
cd alert-service
pip install -r requirements.txt
python -m pytest -v

# Reporting service tests
cd reporting-service
pip install -r requirements.txt
python -m pytest -v
```

### Option 3: Run Integration Tests Only
```bash
# Run only integration tests (requires all services running)
python integration_tests.py
```

### Option 4: Run Specific Test Files
```bash
# Run a specific test file
python -m pytest backend/test_backend.py::test_login_success -v

# Run tests with coverage
pip install pytest-cov
python -m pytest --cov=backend --cov-report=html
```

## Test Database

Tests use a separate test database (`inventory_test`) that is automatically created and cleaned up for each test session. The test database is isolated from your production data.

## Test Categories

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test service interactions and end-to-end workflows
- **API Tests**: Test HTTP endpoints and responses

## CI/CD Integration

The test suite is designed to work with CI/CD pipelines and is fully Jenkins-compatible.

### Option 1: Jenkins Pipeline (Automated)
A complete Jenkins pipeline is configured in the `Jenkinsfile`:
- Automatically runs on code push
- Executes unit and integration tests
- Generates JUnit XML reports
- Publishes coverage reports
- Creates deployment artifacts
- Deploys to staging with approval
- Validates post-deployment

See [CI-CD_SETUP.md](CI-CD_SETUP.md) for detailed Jenkins configuration.

### Option 2: Manual Testing with CI Scripts

**Linux/Mac:**
```bash
# Make script executable
chmod +x run_tests_ci.sh

# Run all tests with CI output formats
./run_tests_ci.sh

# Run specific test types
./run_tests_ci.sh --unit-only
./run_tests_ci.sh --integration-only
./run_tests_ci.sh --verbose
```

### Option 3: GitHub Actions Workflow
```yaml
# Example GitHub Actions workflow
- name: Checkout code
  uses: actions/checkout@v3

- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.10'

- name: Start Services
  run: docker-compose up -d

- name: Wait for Services
  run: sleep 30

- name: Run Tests
  run: |
    chmod +x run_tests_ci.sh
    ./run_tests_ci.sh

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage/coverage.xml
```

## Test Reports and Artifacts

Generated artifacts from CI/CD runs:

### JUnit Reports
Located in `test-results/` after testing:
- `backend-results.xml` - Backend service test results
- `alert-results.xml` - Alert service test results
- `reporting-results.xml` - Reporting service test results
- `summary.txt` - Test summary

### Coverage Reports
Located in `coverage/` after testing:
- `coverage.xml` - Combined coverage in XML format
- `backend/`, `alert/`, `reporting/` - HTML coverage reports
- HTML reports viewable in any web browser

### Deployment Artifacts
Created on successful test completion:
- `inventory-app-{BUILD_NUMBER}.tar.gz` - Complete deployment package
- `BUILD_INFO.txt` - Build metadata
- All service code and Dockerfiles included

### Log Files
Saved in `logs/` directory:
- `*-install.log` - Dependency installation logs
- `*-test.log` - Individual service test logs
- `integration-test.log` - Integration test output
- `ci-run.log` - Overall CI script execution log
- `containers/` - Docker container logs

## Environment Variables for CI

The `.env.ci` file controls CI/CD behavior:

```bash
CI=true                          # Enable CI mode detection
BACKEND_URL=http://backend:5000  # Service URLs (Docker compose network)
ALERT_URL=http://alert_service:5001
REPORTING_URL=http://reporting_service:5002
TEST_TIMEOUT=300                 # Test timeout in seconds
COVERAGE_THRESHOLD=70            # Minimum coverage percentage
COVERAGE_FAIL_UNDER=70           # Fail if coverage below threshold
```

## Jenkins-Specific Features

The testing framework includes Jenkins-specific enhancements:

### 1. **Structured Logging**
- Timestamped log entries
- Log levels: INFO, SUCCESS, ERROR, WARNING
- Both console output and file logging
- Separate log files for each service

### 2. **JUnit XML Reports**
- Pytest configured with `--junit-xml` output
- Automatically parsed by Jenkins
- Test result trends available in Jenkins UI
- Individual test failure details

### 3. **Service Availability Checks**
- Exponential backoff retry logic
- Automatic health checks before testing
- Clear error messages for failed checks
- Timeout safety (10 seconds per request)

### 4. **Exit Codes**
- Exit 0 on complete success
- Exit 1 on any test failure
- Compatible with Jenkins pipeline conditions
- Prevents silent failures

### 5. **CI Environment Detection**
- Automatically detects Jenkins environment
- Disables colored output in CI
- Adjusts logging for log parser
- Sets appropriate timeouts

### 6. **Test Result Aggregation**
```json
// integration-test-report.json generated on each run
{
  "timestamp": "2026-03-19T10:30:00.000Z",
  "total_tests": 10,
  "passed": 9,
  "failed": 1,
  "tests": [
    {
      "name": "Backend Health",
      "status": "PASS",
      "message": "",
      "timestamp": "2026-03-19T10:30:01.000Z"
    },
    ...
  ]
}
```

## Example GitHub Actions workflow
```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    chmod +x run_tests.sh
    ./run_tests.sh

# For integration tests, ensure services are running
- name: Start Services
  run: docker-compose up -d

- name: Wait for Services
  run: sleep 30

- name: Run Integration Tests
  run: python integration_tests.py
```

## Writing New Tests

### Basic Test Structure
```python
import pytest

def test_example(test_client):
    """Test description"""
    response = test_client.get('/endpoint')
    assert response.status_code == 200
    data = response.get_json()
    assert 'expected_key' in data
```

### Testing Authenticated Endpoints
```python
def test_protected_endpoint(auth_token, test_client):
    """Test endpoint requiring authentication"""
    response = test_client.get('/protected-endpoint',
        headers={'Authorization': f'Bearer {auth_token}'})
    assert response.status_code == 200
```

### Database Fixtures
Tests use pytest fixtures for database setup:
- `test_db`: Provides a clean test database
- `test_client`: Flask test client
- `auth_token`: Valid authentication token

## Test Data

Tests include seeded data:
- Test users (admin, manager, employee)
- Sample items with various stock levels
- Test locations and warehouses
- Sample alerts and activity logs

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure PostgreSQL is running
   - Check DB_HOST, DB_USER, DB_PASSWORD environment variables

2. **Import Errors**
   - Install test dependencies: `pip install -r requirements.txt`
   - Ensure you're in the correct service directory

3. **Test Database Issues**
   - Tests automatically create/drop `inventory_test` database
   - Ensure your PostgreSQL user has database creation privileges

### Debug Mode
Run tests with detailed output:
```bash
python -m pytest -v -s --tb=long
```

## Coverage Reports

Generate coverage reports:
```bash
pip install pytest-cov
python -m pytest --cov=. --cov-report=html
# View report in htmlcov/index.html
```

## Performance Testing

For load testing, consider using:
- Locust for API load testing
- JMeter for comprehensive performance tests
- k6 for modern load testing

## Next Steps

- ✅ Integration tests implemented
- Add end-to-end tests with Selenium/WebDriver
- Implement contract testing between services
- Add performance benchmarks
- Set up automated test reporting