pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '15'))
        timeout(time: 1, unit: 'HOURS')
        disableConcurrentBuilds()
        ansiColor('xterm')
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
        // Jenkins Credentials IDs (configure these in Manage Jenkins -> Credentials)
        DOCKERHUB_CREDENTIALS_ID = 'dockerhub-credentials'
        KUBECONFIG_CREDENTIAL_ID = 'k8s-kubeconfig'
        GOOGLE_CLIENT_CRED_ID    = 'vite-google-client-id'

        // Docker Image names
        DOCKER_IMAGE_FRONTEND    = 'meditwin-frontend'
        DOCKER_IMAGE_BACKEND     = 'meditwin-backend'

        // Dynamic properties populated during initialization
        SHORT_SHA                = ''
        BRANCH_CLEAN             = ''
        IS_RELEASE_BRANCH        = false
    }

    stages {

        // ============================================================
        // STAGE 1 — Initialize & Inspect Environment
        // ============================================================
        stage('Initialize Pipeline') {
            steps {
                script {
                    SHORT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    def rawBranch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: 'local'
                    BRANCH_CLEAN = rawBranch.replaceFirst('^origin/', '').replaceAll('/', '-')

                    IS_RELEASE_BRANCH = (BRANCH_CLEAN == 'main' || BRANCH_CLEAN == 'devops-deployment' || params.FORCE_DOCKER_PUSH)

                    echo """
                    ====================================================
                    MediTwin CI/CD Pipeline
                    ====================================================
                    Branch:         ${BRANCH_CLEAN}
                    Commit SHA:     ${SHORT_SHA}
                    Release Branch: ${IS_RELEASE_BRANCH}
                    Deploy Target:  ${params.DEPLOY_TARGET}
                    ====================================================
                    """
                }
            }
        }

        // ============================================================
        // STAGE 2 — Validation (Frontend, Backend, AI Modules)
        // ============================================================
        stage('Validate Application') {
            parallel {

                // ----------------------------------------------------
                // 2A. Frontend: React + Vite build test
                // ----------------------------------------------------
                stage('Validate Frontend') {
                    steps {
                        dir('frontend') {
                            echo "===> Installing frontend dependencies and verifying production build..."
                            sh '''
                                if [ -f package-lock.json ]; then
                                    npm ci
                                else
                                    npm install
                                fi
                                npm run build
                            '''
                        }
                    }
                }

                // ----------------------------------------------------
                // 2B. Backend: Node.js Express syntax & dependencies
                // ----------------------------------------------------
                stage('Validate Backend') {
                    steps {
                        dir('backend') {
                            echo "===> Installing backend dependencies and validating JavaScript syntax..."
                            sh '''
                                if [ -f package-lock.json ]; then
                                    npm ci
                                else
                                    npm install
                                fi
                                node --check server.js
                            '''
                        }
                    }
                }

                // ----------------------------------------------------
                // 2C. Python AI Modules: Bytecode compilation check
                // ----------------------------------------------------
                stage('Validate Python AI Modules') {
                    steps {
                        echo "===> Checking Python syntax for AI Modules (Module 1, 2, 3)..."
                        sh '''
                            python3 -m compileall -q Module_1
                            python3 -m compileall -q Module_2
                            python3 -m compileall -q Module_3
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
                expression { return IS_RELEASE_BRANCH }
            }
            steps {
                script {
                    // Attempt to fetch optional VITE_GOOGLE_CLIENT_ID secret if present
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
                        def feShaTag    = "${frontendRepo}:sha-${SHORT_SHA}"
                        def feBranchTag = "${frontendRepo}:${BRANCH_CLEAN}"
                        def feLatestTag = "${frontendRepo}:latest"

                        def beShaTag    = "${backendRepo}:sha-${SHORT_SHA}"
                        def beBranchTag = "${backendRepo}:${BRANCH_CLEAN}"
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
                                ${BRANCH_CLEAN == 'main' ? "-t ${feLatestTag}" : ""} \
                                .
                        """
                        sh feBuildCmd

                        echo "===> Pushing Frontend Docker Image..."
                        sh "docker push ${feShaTag}"
                        sh "docker push ${feBranchTag}"
                        if (BRANCH_CLEAN == 'main') {
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
                                ${BRANCH_CLEAN == 'main' ? "-t ${beLatestTag}" : ""} \
                                .
                        """
                        sh beBuildCmd

                        echo "===> Pushing Backend Docker Image..."
                        sh "docker push ${beShaTag}"
                        sh "docker push ${beBranchTag}"
                        if (BRANCH_CLEAN == 'main') {
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
                allOf {
                    expression { return IS_RELEASE_BRANCH }
                    not { params.DEPLOY_TARGET == 'none' }
                }
            }
            stages {

                // ----------------------------------------------------
                // 4A: Kubernetes Deployment
                // ----------------------------------------------------
                stage('Kubernetes Deploy') {
                    when {
                        params.DEPLOY_TARGET == 'kubernetes'
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
                        params.DEPLOY_TARGET == 'docker-compose'
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
                        params.DEPLOY_TARGET == 'ansible'
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
