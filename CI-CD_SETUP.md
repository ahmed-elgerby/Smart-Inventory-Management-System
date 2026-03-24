# Jenkins CI/CD Pipeline Documentation

## Overview

This document describes the Jenkins CI/CD pipeline setup for the Inventory Management System. The pipeline automates testing, building, and deployment processes to ensure code quality and rapid iteration.

## Pipeline Architecture

### What's Included
- ✅ Integration tests with service health checks
- ✅ Docker container management
- ✅ Artifact archival
- ✅ Deployment to staging environment
- ✅ Post-deployment validation
- ✅ Comprehensive logging and cleanup

## File Structure

```
├── Jenkinsfile              # Complete pipeline definition
├── .env.ci                  # CI/CD environment variables
├── run_tests_ci.sh         # Linux/Mac CI test runner
├── pytest.ini              # Enhanced with JUnit & coverage
├── integration_tests.py    # Jenkins-compatible test runner
├── test-results/           # Generated: JUnit XML reports
├── coverage/               # Generated: Code coverage reports
└── logs/                   # Generated: Build logs
```

## Jenkins Setup

### Prerequisites
1. **Jenkins Server**: 2.387.1 or later
2. **Plugins Required**:
   - Pipeline
   - Git
   - JUnit Plugin
   - HTML Publisher Plugin
   - Email Extension (optional)
   - Docker Pipeline (optional)

3. **Docker**: Latest version must be installed on Jenkins agents
4. **Python 3.8+**: Required on build agents
5. **Git**: For source control

### Installation Steps

#### Step 1: Install Required Plugins

Navigate to **Jenkins > Manage Jenkins > Manage Plugins**:

1. Search and install:
   - `Pipeline`
   - `junit`
   - `htmlpublisher`
   - `git`
   - `docker-workflow` (optional)

2. Restart Jenkins

#### Step 2: Create New Pipeline Job

1. Click **New Item**
2. Enter job name: `inventory-management-ci`
3. Select **Pipeline**
4. Click **OK**

#### Step 3: Configure Pipeline

In the pipeline job configuration:

1. **General**:
   - ✅ Enable "Discard old builds"
   - Set max builds to keep: `30`
   - Set max artifacts: `10`

2. **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/your-org/inventory-system.git`
   - Branch: `*/main` or your branch
   - Script Path: `Jenkinsfile`

3. **Build Triggers** (optional):
   - GitHub push trigger (if using GitHub)
   - Poll SCM: `H 9 * * 1-5` (daily at 9 AM weekdays)
   - Webhook trigger

4. **Save**

#### Step 4: Configure Jenkins Credentials

1. Go to **Jenkins > Manage Jenkins > Manage Credentials**
2. Add credentials if needed for Git, Docker Registry, etc.
3. Reference them in your Jenkinsfile

## Running Tests

### Option 1: Jenkins Pipeline (Automated)
Just push to the configured repository branch:
```bash
git push origin main
```
Jenkins automatically triggers the pipeline.

### Option 2: Manual Linux/Mac
```bash
# Make script executable
chmod +x run_tests_ci.sh

# Run all tests
./run_tests_ci.sh

# Run unit tests only
./run_tests_ci.sh --unit-only

# Run integration tests only
./run_tests_ci.sh --integration-only

# Run with verbose output
./run_tests_ci.sh --verbose
```

## Pipeline Stages

### 1. **Checkout** 
- Retrieves source code from repository

### 2. **Setup**
- Installs Python dependencies
- Creates test output directories
- Configures environment

### 3. **Build Docker Compose**
- Builds all service Docker images
- Validates image creation

### 4. **Start Services**
- Launches all Docker containers
- Sets up the test environment

### 5. **Wait for Services**
- Health checks for all services
- Retries with exponential backoff
- Maximum 30 attempts (60 seconds total)

### 6. **Integration Tests**
- Tests service-to-service communication
- Validates end-to-end workflows
- Checks alert generation
- Validates reporting functionality

### 7. **Generate Reports**
- Creates summary reports
- Archives test results

### 8. **Publish Results**
- Archives artifacts

### 9. **Cleanup Test Artifacts**
- Removes Python cache files (`__pycache__`, `.pyc`)
- Cleans pytest cache
- Maintains report files

### 10. **Build Artifacts**
- Creates deployment package
- Includes necessary services and configs
- Generates build metadata
- Creates compressed archive

### 11. **Archive Artifacts**
- Stores deployment packages
- Archives test reports

### 12. **Deploy to Staging** (Manual Approval)
- Waits for authorized user approval
- Extracts deployment package
- Starts services in staging environment
- Performs health checks

### 13. **Post-Deployment Validation**
- Runs integration tests against deployed services
- Validates all endpoints
- Ensures data integrity

## Test Results and Reporting

### Test Result Files

Generated in `test-results/` directory:
```
test-results/
└── summary.txt
```

### Accessing Reports from Jenkins

1. Go to your Jenkins job
2. Click the job number (e.g., `#42`)
3. Or download artifacts from "Build Artifacts"

## Environment Variables

The `.env.ci` file controls CI/CD behavior:

```bash
CI=true                          # Enable CI mode
BACKEND_URL=http://backend:5000  # Service URLs
ALERT_URL=http://alert_service:5001
REPORTING_URL=http://reporting_service:5002
TEST_TIMEOUT=300                 # Test timeout in seconds
LOG_LEVEL=INFO                   # Logging verbosity
COVERAGE_THRESHOLD=70            # Minimum coverage %
```

## Troubleshooting

### Services Not Starting
```bash
# Check Docker logs
docker-compose logs

# View specific service logs
docker-compose logs backend

# Recreate containers
docker-compose down -v
docker-compose up -d
```

### Test Failures
1. Check `logs/` directory for detailed logs
2. Review test output in Jenkins console
3. Examine `test-results/` for specific failures
4. Run tests locally with `run_tests_ci.sh --verbose`

### Coverage Reports Not Generated
- Ensure pytest-cov is installed: `pip install pytest-cov`
- Check `.xml` files exist in `coverage/` directory
- Verify coverage thresholds in `pytest.ini`

### Docker Registry Issues
If pulling images from private registry:
1. Configure Docker credentials in Jenkins
2. Use environment variables for registry login
3. Authenticate before building: `docker login -u $USER -p $PASS`

## Performance Optimization

### Parallel Testing
Modify Jenkinsfile to run unit tests in parallel:
```groovy
parallel('Backend Tests': {
    // backend tests
}, 'Alert Tests': {
    // alert tests
}, 'Reporting Tests': {
    // reporting tests
})
```

### Caching
- Docker layer caching speeds up builds
- Python pip cache: Use `--cache-dir`
- Jenkins workspace optimization

### Build Timeout
Current timeout: 1 hour. Adjust in Jenkinsfile:
```groovy
timeout(time: 2, unit: 'HOURS')
```

## Deployment Process

### Manual Deployment
The pipeline requests approval before deploying to staging:
1. Tests must pass
2. User with "inventory-deployers" permission approves
3. Pipeline extracts artifacts
4. Services start in staging environment
5. Post-deployment tests validate setup

### Automated Deployment (Optional)
To enable automatic deployment after successful tests:
1. Remove the `input` block from "Deploy to Staging" stage
2. Uncomment downstream job trigger in post-success

### Production Deployment
For production deployment:
1. Create separate production pipeline
2. Add additional approval requirements
3. Implement blue-green deployment strategy
4. Add database migration steps
5. Include rollback procedures

## Security Considerations

### Secrets Management
1. Use Jenkins Credential System for sensitive data
2. Never commit `.env` files to repository
3. Rotate credentials regularly
4. Use different credentials for each environment

### Access Control
1. Restrict deployment approvers (inventory-deployers group)
2. Limit who can trigger manual builds
3. Audit all pipeline activities
4. Use Jenkins User Authorization Strategy

### Code Quality
1. Implement SAST (Static Application Security Testing)
2. Add dependency vulnerability scanning
3. Review test coverage minimums
4. Enforce linting standards

## Maintenance

### Regular Tasks
- **Weekly**: Review test failures and coverage trends
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Optimize pipeline performance

### Archive Cleanup
Jenkins automatically manages old builds per configured retention policy:
- Keep last 30 builds
- Keep last 10 artifacts
- Auto-delete after 30 days

## Advanced Configurations

### Email Notifications
Uncomment in Jenkinsfile post-failure section:
```groovy
emailext(
    subject: "Test Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
    body: "Pipeline failed. Check console output at ${env.BUILD_URL}console",
    to: "devops-team@example.com"
)
```

### Slack Notifications
Add Slack plugin and configure:
```groovy
slackSend(
    color: (currentBuild.result == 'SUCCESS') ? 'good' : 'danger',
    message: "${env.JOB_NAME} - ${currentBuild.displayName} - ${currentBuild.result}"
)
```

### Integration with Other Tools
- GitHub Status API for PR checks
- JIRA for issue tracking
- Artifactory for artifact storage
- SonarQube for code analysis

## Support and Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Docker daemon not running | Start Docker service |
| Insufficient disk space | Clean Docker images: `docker system prune` |
| Port conflicts | Change ports in `docker-compose.yml` |
| Network issues | Check Docker network: `docker network ls` |
| Python package errors | Clear pip cache: `pip cache purge` |

### Getting Help
1. Check pipeline logs in Jenkins
2. Review test output files
3. Run tests locally with verbose mode
4. Check Docker container logs

## References
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions to Jenkins Migration Guide](https://www.jenkins.io/solutions/github/)
