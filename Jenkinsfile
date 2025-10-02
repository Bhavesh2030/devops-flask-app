pipeline {
  agent any
  options { timestamps() } 

environment {
  APP_NAME   = 'devops-flask-app'
  REGISTRY   = 'docker.io'
  DOCKER_NS  = 'bhavesh530'           // your Docker Hub username
  IMAGE_NAME = "${REGISTRY}/${DOCKER_NS}/${APP_NAME}"   // docker.io/bhavesh530/devops-flask-app
}

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'git rev-parse --short HEAD > .gitsha'
        script { env.VERSION = readFile('.gitsha').trim() }
        echo "Version: ${env.VERSION}"
      }
    }

    stage('Build') {
      steps {
        sh """
          docker build \
            -t ${IMAGE_NAME}:${VERSION} \
            -t ${IMAGE_NAME}:latest .
        """
      }
    }

    stage('Test') {
      steps {
        sh "docker run --rm ${IMAGE_NAME}:${VERSION} pytest -q"
      }
    }

    stage('Code Quality') {
      steps {
        sh "docker run --rm ${IMAGE_NAME}:${VERSION} pylint app.py || true"
        script {
          // Optional SonarQube if you've configured a server called "MySonar"
          try {
            withSonarQubeEnv('MySonar') {
              sh """
                if command -v sonar-scanner >/dev/null 2>&1; then
                  sonar-scanner \
                    -Dsonar.projectKey=${APP_NAME} \
                    -Dsonar.projectName=${APP_NAME} \
                    -Dsonar.sources=. \
                    -Dsonar.python.version=3.10
                else
                  echo 'SonarScanner missing on this agent — skipping Sonar step.';
                fi
              """
            }
          } catch (e) { echo "Sonar step skipped: ${e}" }
        }
      }
    }

    stage('Security') {
      steps {
        sh "docker run --rm ${IMAGE_NAME}:${VERSION} bandit -r . || true"
        sh """
          if command -v trivy >/dev/null 2>&1; then
            trivy image --severity HIGH,CRITICAL --ignore-unfixed --no-progress ${IMAGE_NAME}:${VERSION} || true
          else
            echo 'Trivy not installed — skipping image scan.'
          fi
        """
      }
    }

    stage('Deploy: Staging') {
      steps {
        sh """
          echo "IMAGE_NAME=${IMAGE_NAME}" > .env.staging
          echo "IMAGE_TAG=${VERSION}"    >> .env.staging
          docker compose -f docker-compose.staging.yml --env-file .env.staging pull
          docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --force-recreate
          sleep 3
          curl -fsS http://localhost:5000/health
        """
      }
    }

    stage('Release: Push to Registry') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'DOCKERHUB', usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
          sh """
            echo "${DH_TOKEN}" | docker login -u "${DH_USER}" --password-stdin
            docker push ${IMAGE_NAME}:${VERSION}
            docker push ${IMAGE_NAME}:latest
            docker logout
          """
        }
      }
    }

    stage('Monitoring & Alert') {
      steps {
        script {
          def ok = sh(returnStatus: true, script: "curl -fsS http://localhost:5000/health >/dev/null") == 0
          if (!ok) {
            echo 'Health check failed — sending alert (if webhook configured).'
            withCredentials([string(credentialsId: 'SLACK_WEBHOOK', variable: 'SLACK_URL')]) {
              sh """[ -n "$SLACK_URL" ] && curl -X POST -H 'Content-type: application/json' \
                --data '{"text":"🚨 devops-flask-app health check FAILED on staging"}' "$SLACK_URL" || true"""
            }
            error('Staging health check failed.')
          } else {
            echo 'Health check OK.'
          }
        }
      }
    }

    stage('Deploy: Production (optional)') {
      when { expression { return env.DEPLOY_PROD?.trim() == 'true' } }
      steps {
        sh """
          echo "IMAGE_NAME=${IMAGE_NAME}" > .env.prod
          echo "IMAGE_TAG=${VERSION}"    >> .env.prod
          docker compose -f docker-compose.prod.yml --env-file .env.prod pull
          docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate
        """
      }
    }
  }

  post {
    success { echo "Pipeline OK: ${IMAGE_NAME}:${VERSION}" }
    failure { echo "Pipeline failed — check stage logs." }
  }
}
