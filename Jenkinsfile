pipeline {
    agent any
    
    options {
        // Prevent concurrent builds
        disableConcurrentBuilds()
        // Keep builds for 30 days
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        // Add timestamps to console output
        timestamps()
        // Set timeout to prevent hanging builds
        timeout(time: 1, unit: 'HOURS')
    }
    
    environment {
        // CI environment variable for Python scripts to detect Jenkins
        CI = 'true'
        JENKINS_HOME = "${env.JENKINS_HOME}"
        // Test output directories
        TEST_RESULTS_DIR = 'test-results'
        COVERAGE_DIR = 'coverage'
        // Service URLs for testing
        BACKEND_URL = 'http://localhost:5000'
        ALERT_URL = 'http://localhost:5001'
        REPORTING_URL = 'http://localhost:5002'
        // Python environment
        PYTHONUNBUFFERED = '1'
        PYTHONPATH = '.'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo '📥 Checking out source code...'
                checkout scm
            }
        }
        
        stage('Setup') {
            steps {
                echo '⚙️ Setting up test environment...'
                script {
                    sh '''
                        # Create test results directory
                        mkdir -p ${TEST_RESULTS_DIR}
                        
                        # Install global dependencies
                        python3 -m pip install --upgrade pip setuptools wheel
                        python3 -m pip install requests
                        
                        # Log Python version
                        echo "Python version:"
                        python3 --version
                        
                        # Log pip packages
                        echo "Installed packages:"
                        pip3 list
                    '''
                }
            }
        }
        
        stage('Build Docker Compose') {
            steps {
                echo '🐳 Building Docker compose services...'
                script {
                    sh '''
                        # Build all services
                        docker-compose build --no-cache
                        
                        # Verify images were created
                        docker images | grep -E 'claudelast|postgres'
                    '''
                }
            }
        }
        
        stage('Start Services') {
            steps {
                echo '🚀 Starting services...'
                script {
                    sh '''
                        # Start services in background
                        docker-compose up -d
                        
                        # Wait for services to be healthy
                        echo "Waiting for services to be ready..."
                        sleep 5
                        
                        # Check service status
                        docker-compose ps
                    '''
                }
            }
        }
        
        stage('Wait for Services') {
            steps {
                echo '⏳ Waiting for services to be ready...'
                script {
                    sh '''
                        # Wait script with retry logic
                        max_attempts=30
                        attempt=0
                        
                        while [ $attempt -lt $max_attempts ]; do
                            echo "Attempt $((attempt + 1))/$max_attempts..."
                            
                            # Check backend health
                            if curl -f http://localhost:5000/health 2>/dev/null; then
                                echo "✅ Backend is healthy"
                                break
                            fi
                            
                            attempt=$((attempt + 1))
                            if [ $attempt -lt $max_attempts ]; then
                                sleep 2
                            fi
                        done
                        
                        if [ $attempt -eq $max_attempts ]; then
                            echo "❌ Services did not become healthy in time"
                            docker-compose logs
                            exit 1
                        fi
                    '''
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                echo '🔗 Running integration tests...'
                script {
                    sh '''
                        # Install dependencies
                        pip install requests
                        
                        # Run integration tests
                        python3 integration_tests.py
                        
                        # Integration test exit code will determine stage result
                    '''
                }
            }
        }
        
        stage('Generate Reports') {
            steps {
                echo '📊 Generating test reports...'
                script {
                    sh '''
                        # List all test results
                        if [ -d test-results ]; then
                            echo "Test results:"
                            ls -la test-results/
                        fi
                    '''
                }
            }
        }
        
        stage('Publish Results') {
            steps {
                echo '📤 Publishing test results...'
                script {
                    // Archive artifacts
                    archiveArtifacts artifacts: 'test-results/**/*.xml,coverage/**/*.xml', 
                                     allowEmptyArchive: true
        
        stage('Cleanup Test Artifacts') {
            steps {
                echo '🧹 Cleaning up test artifacts...'
                script {
                    sh '''
                        # Remove temporary test files but keep reports
                        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
                        find . -type f -name "*.pyc" -delete 2>/dev/null || true
                        find . -type f -name "*.pyo" -delete 2>/dev/null || true
                        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
                        
                        echo "✅ Test artifacts cleaned"
                    '''
                }
            }
        }
        
        stage('Build Artifacts') {
            when {
                expression {
                    return currentBuild.result == null || currentBuild.result == 'SUCCESS'
                }
            }
            steps {
                echo '📦 Building deployment artifacts...'
                script {
                    sh '''
                        # Create deployment archive with only necessary files
                        echo "📦 Creating deployment package..."
                        
                        # Create deployment directory
                        mkdir -p deployment
                        
                        # Copy service code and Dockerfiles
                        cp -r backend deployment/
                        cp -r alert-service deployment/
                        cp -r reporting-service deployment/
                        cp -r DB deployment/
                        cp -r FrontEnd deployment/
                        
                        # Copy docker-compose and related files
                        cp docker-compose.yml deployment/
                        cp .env.ci deployment/
                        
                        # Create metadata file
                        cat > deployment/BUILD_INFO.txt <<EOF
Build Information
=================
Build Number: ${BUILD_NUMBER}
Build ID: ${BUILD_ID}
Build URL: ${BUILD_URL}
Git Commit: ${GIT_COMMIT}
Git Branch: ${GIT_BRANCH}
Timestamp: $(date -Iseconds)
EOF
                        
                        # Create archive
                        tar -czf "inventory-app-${BUILD_NUMBER}.tar.gz" deployment/
                        
                        echo "✅ Deployment artifact created: inventory-app-${BUILD_NUMBER}.tar.gz"
                        ls -lh inventory-app-${BUILD_NUMBER}.tar.gz
                    '''
                }
            }
        }
        
        stage('Archive Artifacts') {
            when {
                expression {
                    return currentBuild.result == null || currentBuild.result == 'SUCCESS'
                }
            }
            steps {
                echo '📤 Archiving build artifacts...'
                script {
                    archiveArtifacts artifacts: 'inventory-app-*.tar.gz', 
                                     allowEmptyArchive: true,
                                     onlyIfSuccessful: true
                    
                    archiveArtifacts artifacts: 'test-results/**/*.xml,coverage/**/*.xml', 
                                     allowEmptyArchive: true
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                expression {
                    return currentBuild.result == null || currentBuild.result == 'SUCCESS'
                }
            }
            input {
                message "Deploy to staging environment?"
                ok "Deploy"
                submitter "inventory-deployers"
            }
            steps {
                echo '🚀 Deploying to staging environment...'
                script {
                    sh '''
                        echo "📦 Preparing deployment..."
                        
                        # Extract deployment package
                        DEPLOY_DIR="inventory-app-${BUILD_NUMBER}"
                        tar -xzf "inventory-app-${BUILD_NUMBER}.tar.gz"
                        
                        # Display deployment info
                        cat "deployment/BUILD_INFO.txt"
                        
                        echo "🚀 Starting deployment process..."
                        
                        # Deploy using docker-compose
                        cd deployment
                        
                        # Stop existing containers
                        docker-compose down -v || true
                        
                        # Start new containers
                        docker-compose up -d
                        
                        # Wait for services to be healthy
                        sleep 10
                        docker-compose ps
                        
                        # Health check
                        echo "🏥 Performing health check..."
                        for i in {1..5}; do
                            if curl -f http://localhost:5000/health; then
                                echo "✅ Deployment successful"
                                break
                            fi
                            if [ $i -eq 5 ]; then
                                echo "❌ Deployment health check failed"
                                exit 1
                            fi
                            sleep 5
                        done
                        
                        cd ..
                    '''
                }
            }
        }
        
        stage('Post-Deployment Validation') {
            when {
                expression {
                    return currentBuild.result == null || currentBuild.result == 'SUCCESS'
                }
            }
            steps {
                echo '✅ Validating deployment...'
                script {
                    sh '''
                        echo "🔍 Running post-deployment validation..."
                        
                        # Run smoke tests
                        python3 integration_tests.py
                        
                        if [ $? -eq 0 ]; then
                            echo "✅ Post-deployment validation passed"
                        else
                            echo "❌ Post-deployment validation failed"
                            exit 1
                        fi
                    '''
                }
            }
        }
    }
    
    post {
        always {
            echo '🧹 Cleaning up...'
            script {
                // Collect logs from containers
                sh '''
                    # Create logs directory for archival
                    mkdir -p logs/containers
                    
                    echo "=== Backend Logs ===" > logs/containers/backend.log
                    docker-compose logs backend >> logs/containers/backend.log 2>&1 || true
                    
                    echo "=== Alert Service Logs ===" > logs/containers/alert_service.log
                    docker-compose logs alert_service >> logs/containers/alert_service.log 2>&1 || true
                    
                    echo "=== Reporting Service Logs ===" > logs/containers/reporting_service.log
                    docker-compose logs reporting_service >> logs/containers/reporting_service.log 2>&1 || true
                    
                    echo "=== Database Logs ===" > logs/containers/database.log
                    docker-compose logs db >> logs/containers/database.log 2>&1 || true
                    
                    echo "=== Nginx Logs ===" > logs/containers/nginx.log
                    docker-compose logs nginx >> logs/containers/nginx.log 2>&1 || true
                '''
                
                // Archive container logs
                archiveArtifacts artifacts: 'logs/**/*.log', 
                                 allowEmptyArchive: true
                
                // Clean up temporary deployment directory
                sh '''
                    rm -rf deployment 2>/dev/null || true
                    echo "✅ Temporary files cleaned"
                '''
            }
        }
        
        success {
            echo '✅ Pipeline completed successfully!'
            script {
                // Log success
                sh '''
                    echo "🎉 Build #${BUILD_NUMBER} - SUCCESS"
                    echo "All tests passed and deployment artifacts created"
                '''
                
                // Optional: trigger downstream jobs
                // build job: 'DeployInventorySystem', wait: false, parameters: [
                //     string(name: 'ARTIFACT', value: "inventory-app-${BUILD_NUMBER}.tar.gz")
                // ]
            }
        }
        
        failure {
            echo '❌ Pipeline failed!'
            script {
                sh '''
                    echo "❌ Build #${BUILD_NUMBER} - FAILED"
                    echo "Check logs for details"
                '''
                
                // Optional: send failure notifications
                // emailext(
                //     subject: "Test Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                //     body: "Pipeline failed. Check console output at ${env.BUILD_URL}console",
                //     to: "devops-team@example.com"
                // )
            }
        }
        
        unstable {
            echo '⚠️ Pipeline unstable - tests passed but with warnings'
        }
        
        cleanup {
            echo '🧹 Final cleanup and container shutdown...'
            script {
                sh '''
                    # Stop all services
                    docker-compose down -v 2>/dev/null || true
                    
                    # Remove dangling images
                    docker image prune -f 2>/dev/null || true
                    
                    # Clean build cache
                    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
                    find . -type f -name "*.pyc" -delete 2>/dev/null || true
                    
                    echo "✅ Final cleanup complete"
                '''
            }
        }
    }
}
