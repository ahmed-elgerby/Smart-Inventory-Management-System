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
                    python3 -m venv ci_env
                    . ci_env/bin/activate
                    pip install --upgrade pip setuptools wheel requests
                    deactivate
                '''
            }
        }
        
        stage('Build & Test Services') {
            steps {
                sh '''
                    #building and starting services via docker-compose
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
                    
                    # Run unit tests for each service
                    echo "Running unit tests..."
                    
                    # Backend tests
                    docker-compose exec -T backend pytest -v --tb=short || exit 1
                    
                    # Alert service tests  
                    docker-compose exec -T alert-service pytest -v --tb=short || exit 1
                    
                    # Reporting service tests
                    docker-compose exec -T reporting-service pytest -v --tb=short || exit 1
                    
                    # Integration tests
                    . ci_env/bin/activate
                    python3 integration_tests.py
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
        
        stage('Deploy to Staging') {
            when { expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' } }
            input { message "Deploy to staging?" }
            steps {
                sh '''
                    tar -xzf "inventory-app-${BUILD_NUMBER}.tar.gz"
                    cd deployment
                    docker-compose down -v || true
                    docker-compose up -d
                    sleep 10
                    
                    for i in {1..5}; do
                        curl -f ${BACKEND_URL}/health && break
                        [ $i -eq 5 ] && exit 1
                        sleep 5
                    done
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
                docker image prune -f || true
                rm -rf ci_env deployment __pycache__ *.pyc .pytest_cache || true
            '''
        }
    }
}


