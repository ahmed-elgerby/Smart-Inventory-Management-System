pipeline {
    agent any
    
    environment {
        CI = 'true'
        TEST_RESULTS_DIR = 'test-results'
        BACKEND_URL = 'http://localhost:5000'
        PYTHONUNBUFFERED = '1'
        PYTHONPATH = '.'
    }
    
    stages {        
        stage('Setup') {
            steps {
                sh '''
                    mkdir -p ${TEST_RESULTS_DIR}

                    # Ensure Python venv package is installed
                    apt-get update && apt-get install -y python3.12-venv

                    # Try virtual env
                    if python3 -m venv ci_env; then
                        . ci_env/bin/activate
                        pip install --upgrade pip setuptools wheel requests
                        deactivate
                    else
                        echo "venv creation failed, using isolated project install"
                        python3 -m pip install --upgrade pip setuptools wheel requests --target ./ci_env_lib --break-system-packages
                        export PYTHONPATH="$PWD/ci_env_lib:$PYTHONPATH"
                    fi
                '''
            }
        }
        
        stage('Build & Test Services') {
            steps {
                sh '''
                    # Clean up any existing containers and volumes
                    docker-compose down -v || true
                    
                    # Build and start services
                    docker-compose up --build -d
                    sleep 5
                    
                    # Health check with retry
                    for i in {1..30}; do
                        if curl -f ${BACKEND_URL}/health 2>/dev/null; then
                            echo "Services ready"
                            break
                        fi
                        [ $i -eq 30 ] && exit 1
                        sleep 2
                    done
                    
                    echo "Running unit tests..."
                '''
                
                // Retry block for backend tests
                retry(2) {
                    sh 'docker-compose exec -T backend pytest -v --tb=short'
                }
                
                // Retry block for alert service tests
                retry(2) {
                    sh 'docker-compose exec -T alert_service pytest -v --tb=short'
                }
                
                // Retry block for reporting service tests
                retry(2) {
                    sh 'docker-compose exec -T reporting_service pytest -v --tb=short'
                }
                
                // Integration tests
                sh '''
                    . ci_env/bin/activate
                    python3 integration_tests.py
                    deactivate
                '''
            }
        }
        
        stage('Pushing to Docker Hub') {
            steps {
                // Only push all images created if tests passed
                sh '''
                    docker push ahmedilgerby/inventory_db:latest
                    docker push ahmedilgerby/inventory_be:latest
                    docker push ahmedilgerby/inventory_alert_service:latest
                    docker push ahmedilgerby/inventory_reporting_service:latest
                    docker push ahmedilgerby/inventory_frontend:latest
                '''
            }
        }

        stage('Build Artifacts') {
            when { expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' } }
            steps {
                sh '''
                    mkdir -p deployment
                    cp -r backend alert-service reporting-service DB FrontEnd deployment/
                    cp docker-compose.yml .env.ci deployment/ 2>/dev/null || true
                    
                    cat > deployment/BUILD_INFO.txt <<EOF
Build: ${BUILD_NUMBER}
Commit: ${GIT_COMMIT}
EOF
                    
                    tar -czf "inventory-app-${BUILD_NUMBER}.tar.gz" deployment/
                '''
            }
        }
    }
    
    post {
        always {
            sh '''
                mkdir -p logs
                docker-compose logs > logs/containers.log 2>&1 || true
            '''
            archiveArtifacts artifacts: 'logs/**/*.log,test-results/**/*.xml,inventory-app-*.tar.gz', allowEmptyArchive: true
        }
        
        cleanup {
            sh '''
                docker-compose down -v || true
                rm -rf ci_env deployment __pycache__ *.pyc .pytest_cache || true
            '''
        }
    }
}
