pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '15'))
        timeout(time: 1, unit: 'HOURS')
        disableConcurrentBuilds()
        timestamps()
    }

    parameters {
        choice(
            name: 'DEPLOY_TARGET',
            choices: ['kubernetes', 'docker-compose', 'ansible', 'none'],
            description: 'Select deployment strategy/target'
        )
        booleanParam(
            name: 'FORCE_DOCKER_PUSH',
            defaultValue: false,
            description: 'Force Docker image build and push regardless of branch'
        )
    }

    environment {
        // Jenkins Credentials IDs (configure in Manage Jenkins -> Credentials)
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub-credentials'
        KUBECONFIG_CREDENTIAL_ID = 'k8s-kubeconfig'
        GOOGLE_CLIENT_CRED_ID    = 'vite-google-client-id'

        // Docker Image names
        DOCKER_IMAGE_FRONTEND    = 'meditwin-frontend'
        DOCKER_IMAGE_BACKEND     = 'meditwin-backend'
    }

    stages {

        // ============================================================
        // STAGE 1 — Initialize & Inspect Environment
        // ============================================================
        stage('Initialize Pipeline') {
            steps {
                script {
                    env.SHORT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    def rawBranch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: 'local'
                    env.BRANCH_CLEAN = rawBranch.replaceFirst('^origin/', '').replaceAll('/', '-')

                    def isRelease = (env.BRANCH_CLEAN == 'main' || env.BRANCH_CLEAN == 'devops-deployment' || params.FORCE_DOCKER_PUSH.toString().toBoolean())
                    env.IS_RELEASE_BRANCH = isRelease.toString()

                    echo """
                    ====================================================
                    MediTwin CI/CD Pipeline
                    ====================================================
                    Branch:         ${env.BRANCH_CLEAN}
                    Commit SHA:     ${env.SHORT_SHA}
                    Release Branch: ${env.IS_RELEASE_BRANCH}
                    Deploy Target:  ${params.DEPLOY_TARGET}
                    ====================================================
                    """

                    sh '''
                        echo "===> Checking Agent Environment Tools:"
                        echo -n "Node.js: " && (command -v node || echo "not found")
                        echo -n "npm:     " && (command -v npm || echo "not found")
                        echo -n "Python3: " && (command -v python3 || echo "not found")
                        echo -n "Docker:  " && (command -v docker || echo "not found")
                        echo -n "kubectl: " && (command -v kubectl || echo "not found")
                    '''
                }
            }
        }

        // ============================================================
        // STAGE 2 — Validation (Frontend, Backend, AI Modules)
        // Supports both host runtime and containerized fallback
        // ============================================================
        stage('Validate Application') {
            parallel {

                // ----------------------------------------------------
                // 2A. Frontend: React + Vite build test
                // ----------------------------------------------------
                stage('Validate Frontend') {
                    steps {
                        script {
                            def googleClientId = ""
                            try {
                                withCredentials([string(credentialsId: env.GOOGLE_CLIENT_CRED_ID, variable: 'CLIENT_ID')]) {
                                    googleClientId = CLIENT_ID
                                }
                            } catch (Exception e) {}

                            sh """
                                if command -v npm >/dev/null 2>&1; then
                                    echo "===> Validating Frontend using host Node.js / npm..."
                                    cd frontend
                                    if [ -f package-lock.json ]; then npm ci; else npm install; fi
                                    npm run build
                                elif command -v docker >/dev/null 2>&1; then
                                    echo "===> 'npm' not found on agent. Validating Frontend build via Docker (node:22-bookworm-slim)..."
                                    docker build --target build \
                                        -f ./frontend/Dockerfile \
                                        --build-arg VITE_GOOGLE_CLIENT_ID="${googleClientId}" \
                                        .
                                else
                                    echo "===> ERROR: Neither 'npm' nor 'docker' is available on this Jenkins agent."
                                    echo "Please install Node.js/npm or Docker on your Jenkins agent to validate the frontend."
                                    exit 1
                                fi
                            """
                        }
                    }
                }

                // ----------------------------------------------------
                // 2B. Backend: Node.js Express syntax & dependencies
                // ----------------------------------------------------
                stage('Validate Backend') {
                    steps {
                        sh '''
                            if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
                                echo "===> Validating Backend using host Node.js / npm..."
                                cd backend
                                if [ -f package-lock.json ]; then npm ci; else npm install; fi
                                node --check server.js
                            elif command -v docker >/dev/null 2>&1; then
                                echo "===> 'node/npm' not found on agent. Validating Backend syntax via Docker (node:22-bookworm-slim)..."
                                tar -cf - backend | docker run --rm -i node:22-bookworm-slim sh -c "
                                    tar -xf -
                                    cd backend
                                    if [ -f package-lock.json ]; then npm ci --omit=dev; else npm install --omit=dev; fi
                                    node --check server.js
                                "
                            else
                                echo "===> ERROR: Neither 'node/npm' nor 'docker' is available on this Jenkins agent."
                                echo "Please install Node.js/npm or Docker on your Jenkins agent to validate the backend."
                                exit 1
                            fi
                        '''
                    }
                }

                // ----------------------------------------------------
                // 2C. Python AI Modules: Bytecode compilation check
                // ----------------------------------------------------
                stage('Validate Python AI Modules') {
                    steps {
                        sh '''
                            if command -v python3 >/dev/null 2>&1; then
                                echo "===> Validating Python AI Modules using host python3..."
                                python3 -m compileall -q Module_1
                                python3 -m compileall -q Module_2
                                python3 -m compileall -q Module_3
                            elif command -v docker >/dev/null 2>&1; then
                                echo "===> 'python3' not found on agent. Validating AI Modules via Docker (python:3.11-slim)..."
                                tar -cf - Module_1 Module_2 Module_3 | docker run --rm -i python:3.11-slim sh -c "
                                    tar -xf -
                                    python3 -m compileall -q Module_1
                                    python3 -m compileall -q Module_2
                                    python3 -m compileall -q Module_3
                                "
                            else
                                echo "===> ERROR: Neither 'python3' nor 'docker' is available on this Jenkins agent."
                                echo "Please install python3 or Docker on your Jenkins agent to validate AI modules."
                                exit 1
                            fi
                        '''
                    }
                }
            }
        }

        // ============================================================
        // STAGE 3 — Docker Build & Publish to Registry
        // ============================================================
        stage('Docker Build & Push') {
            when {
                expression { return env.IS_RELEASE_BRANCH == 'true' }
            }
            steps {
                script {
                    def googleClientId = ""
                    try {
                        withCredentials([string(credentialsId: env.GOOGLE_CLIENT_CRED_ID, variable: 'CLIENT_ID')]) {
                            googleClientId = CLIENT_ID
                        }
                    } catch (Exception e) {
                        echo "Notice: '${env.GOOGLE_CLIENT_CRED_ID}' secret not found in Jenkins credentials; proceeding with empty client id."
                    }

                    withCredentials([usernamePassword(
                        credentialsId: env.DOCKERHUB_CREDENTIALS_ID,
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        echo "===> Logging in to Docker Hub registry..."
                        sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'

                        def frontendRepo = "${DOCKER_USER}/${env.DOCKER_IMAGE_FRONTEND}"
                        def backendRepo  = "${DOCKER_USER}/${env.DOCKER_IMAGE_BACKEND}"

                        // Generate tag variants mirroring GitHub Actions
                        def feShaTag    = "${frontendRepo}:sha-${env.SHORT_SHA}"
                        def feBranchTag = "${frontendRepo}:${env.BRANCH_CLEAN}"
                        def feLatestTag = "${frontendRepo}:latest"

                        def beShaTag    = "${backendRepo}:sha-${env.SHORT_SHA}"
                        def beBranchTag = "${backendRepo}:${env.BRANCH_CLEAN}"
                        def beLatestTag = "${backendRepo}:latest"

                        // --------------------------------------------
                        // Build & Push Frontend Image
                        // Uses repository root context so frontend/nginx.conf is available
                        // --------------------------------------------
                        echo "===> Building Frontend Docker Image..."
                        def feBuildCmd = """
                            docker build \
                                -f ./frontend/Dockerfile \
                                --build-arg VITE_GOOGLE_CLIENT_ID="${googleClientId}" \
                                -t ${feShaTag} \
                                -t ${feBranchTag} \
                                ${env.BRANCH_CLEAN == 'main' ? "-t ${feLatestTag}" : ""} \
                                .
                        """
                        sh feBuildCmd

                        echo "===> Pushing Frontend Docker Image..."
                        sh "docker push ${feShaTag}"
                        sh "docker push ${feBranchTag}"
                        if (env.BRANCH_CLEAN == 'main') {
                            sh "docker push ${feLatestTag}"
                        }

                        // --------------------------------------------
                        // Build & Push Backend Image
                        // Uses repository root context to copy backend + Module_1/2/3
                        // --------------------------------------------
                        echo "===> Building Backend Docker Image..."
                        def beBuildCmd = """
                            docker build \
                                -f ./backend/Dockerfile \
                                -t ${beShaTag} \
                                -t ${beBranchTag} \
                                ${env.BRANCH_CLEAN == 'main' ? "-t ${beLatestTag}" : ""} \
                                .
                        """
                        sh beBuildCmd

                        echo "===> Pushing Backend Docker Image..."
                        sh "docker push ${beShaTag}"
                        sh "docker push ${beBranchTag}"
                        if (env.BRANCH_CLEAN == 'main') {
                            sh "docker push ${beLatestTag}"
                        }
                    }
                }
            }
        }

        // ============================================================
        // STAGE 4 — Continuous Deployment (CD)
        // ============================================================
        stage('Deploy Application') {
            when {
                expression { return env.IS_RELEASE_BRANCH == 'true' && params.DEPLOY_TARGET != 'none' }
            }
            stages {

                // ----------------------------------------------------
                // 4A: Kubernetes Deployment
                // ----------------------------------------------------
                stage('Kubernetes Deploy') {
                    when {
                        expression { return params.DEPLOY_TARGET == 'kubernetes' }
                    }
                    steps {
                        script {
                            echo "===> Deploying to Kubernetes Cluster..."
                            try {
                                withCredentials([file(credentialsId: env.KUBECONFIG_CREDENTIAL_ID, variable: 'KUBECONFIG')]) {
                                    sh '''
                                        kubectl apply -f k8s/namespace.yaml
                                        kubectl apply -f k8s/mongodb.yaml
                                        kubectl apply -f k8s/backend.yaml
                                        kubectl apply -f k8s/frontend.yaml

                                        echo "Verifying deployment rollouts..."
                                        kubectl rollout status deployment/backend -n meditwin --timeout=180s || true
                                        kubectl rollout status deployment/frontend -n meditwin --timeout=180s || true
                                    '''
                                }
                            } catch (Exception e) {
                                echo "Notice: Jenkins '${env.KUBECONFIG_CREDENTIAL_ID}' not set; using agent default kubeconfig context..."
                                sh '''
                                    kubectl apply -f k8s/namespace.yaml
                                    kubectl apply -f k8s/mongodb.yaml
                                    kubectl apply -f k8s/backend.yaml
                                    kubectl apply -f k8s/frontend.yaml

                                    echo "Verifying deployment rollouts..."
                                    kubectl rollout status deployment/backend -n meditwin --timeout=180s || true
                                    kubectl rollout status deployment/frontend -n meditwin --timeout=180s || true
                                '''
                            }
                        }
                    }
                }

                // ----------------------------------------------------
                // 4B: Docker Compose Deployment
                // ----------------------------------------------------
                stage('Docker Compose Deploy') {
                    when {
                        expression { return params.DEPLOY_TARGET == 'docker-compose' }
                    }
                    steps {
                        echo "===> Deploying with Docker Compose..."
                        sh '''
                            docker compose down --remove-orphans || true
                            docker compose up -d --build
                            docker compose ps
                        '''
                    }
                }

                // ----------------------------------------------------
                // 4C: Ansible Playbook Orchestration
                // ----------------------------------------------------
                stage('Ansible Provision & Deploy') {
                    when {
                        expression { return params.DEPLOY_TARGET == 'ansible' }
                    }
                    steps {
                        echo "===> Running Ansible Playbook..."
                        dir('ansible') {
                            sh '''
                                ansible-playbook -i inventory.ini playbook.yml
                            '''
                        }
                    }
                }
            }
        }
    }

    // ============================================================
    // Post-execution handlers & Workspace Cleanup
    // ============================================================
    post {
        always {
            echo "===> MediTwin pipeline run completed."
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
        success {
            echo "===> SUCCESS: MediTwin build and deployment completed successfully!"
        }
        failure {
            echo "===> FAILURE: MediTwin pipeline encountered errors. Inspect logs above."
        }
    }
}
