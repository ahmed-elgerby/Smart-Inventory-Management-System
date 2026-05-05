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
                        pip install --upgrade pip setuptools wheel requests ansible
                        deactivate
                    else
                        echo "venv creation failed, using isolated project install"
                        python3 -m pip install --upgrade pip setuptools wheel requests ansible --target ./ci_env_lib --break-system-packages
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
                    sh 'docker-compose exec -T alert-service pytest -v --tb=short'
                }
                
                // Retry block for reporting service tests
                retry(2) {
                    sh 'docker-compose exec -T reporting-service pytest -v --tb=short'
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
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                }
                sh '''
                    set -e
                    if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
                        git diff --quiet HEAD~1 HEAD -- DB backend alert-service reporting-service FrontEnd docker-compose.yml || CHANGED=1
                    else
                        CHANGED=1
                    fi

                    if [ -z "$CHANGED" ]; then
                        echo "No relevant image source changes detected. Skipping Docker push."
                        exit 0
                    fi

                    echo "Changes detected. Pushing updated Docker images..."
                    docker push ahmedilgerby/inventory_db:latest &
                    docker push ahmedilgerby/inventory_be:latest &
                    docker push ahmedilgerby/inventory_alert_service:latest &
                    docker push ahmedilgerby/inventory_reporting_service:latest &
                    docker push ahmedilgerby/inventory_frontend:latest &
                    wait
                '''
            }
        }

        stage('Terraform Deploy') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
                    sh '''
                        set -e
                        cd Cloud
                        export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
                        export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
                        terraform init -input=false
                        terraform apply -auto-approve
                    '''
                }
            }
        }
        stage('Ansible Provision & Deploy K8S') {
            steps {
                sh '''
                    set -e
                    . ci_env/bin/activate
                    cd Cloud
                    
                    export ANSIBLE_HOST_KEY_CHECKING=False
                    
                    # Run EC2 provisioning
                    ansible-playbook -i hosts.ini ec2-provision.yml -o StrictHostKeyChecking=no
                    
                    # Copy K8S files via ansible and deploy
                    ansible-playbook -i hosts.ini deploy-k8s.yml -o StrictHostKeyChecking=no
                '''
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
                    sh '''
                        # Output ALB DNS name
                        echo ""
                        echo "========================================"
                        echo "Deployment Complete!"
                        echo "========================================"
                        cd Cloud
                        terraform output -raw aws_lb_inventory_alb_dns_name || echo "ALB DNS not yet available, check AWS console"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            sh '''
                mkdir -p logs
                docker-compose logs > logs/containers.log 2>&1 || true
            '''
            archiveArtifacts artifacts: 'logs/**/*.log,test-results/**/*.xml', allowEmptyArchive: true
        }
        
        cleanup {
            sh '''
                docker-compose down -v || true
                rm -rf ci_env __pycache__ *.pyc .pytest_cache || true
            '''
        }
    }
}
