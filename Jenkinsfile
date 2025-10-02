pipeline {
  agent any
  options { timestamps() }

  environment {
    APP_NAME   = 'devops-flask-app'
    REGISTRY   = 'docker.io'
    DOCKER_NS  = 'bhavesh530'                   // your Docker Hub username
    IMAGE_NAME = "${REGISTRY}/${DOCKER_NS}/${APP_NAME}"   // docker.io/bhavesh530/devops-flask-app
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        bat 'git rev-parse --short HEAD > .gitsha'
        script { env.VERSION = readFile('.gitsha').trim() }
        echo "Version: ${env.VERSION}"
      }
    }

    stage('Build') {
      steps {
        bat """
          docker build -t ${IMAGE_NAME}:${VERSION} -t ${IMAGE_NAME}:latest .
        """
      }
    }

    stage('Test') {
      steps {
        bat "docker run --rm ${IMAGE_NAME}:${VERSION} pytest -q"
      }
    }

    stage('Code Quality') {
      steps {
        bat "docker run --rm ${IMAGE_NAME}:${VERSION} pylint app.py || ver >NUL"
        script {
          // Optional SonarQube (skips cleanly if not configured)
          try {
            withSonarQubeEnv('MySonar') {
              bat """
                where sonar-scanner >NUL 2>&1 && sonar-scanner ^
                  -Dsonar.projectKey=${APP_NAME} ^
                  -Dsonar.projectName=${APP_NAME} ^
                  -Dsonar.sources=. ^
                  -Dsonar.python.version=3.10 || echo SonarScanner missing - skipping
              """
            }
          } catch (e) { echo "Sonar step skipped: ${e}" }
        }
      }
    }

    stage('Security') {
      steps {
        // Bandit runs inside the built image
        bat "docker run --rm ${IMAGE_NAME}:${VERSION} bandit -r . || ver >NUL"

        // Trivy: use host install if present; otherwise skip (pipeline continues)
        bat '''
          where trivy >NUL 2>&1
          if %ERRORLEVEL% EQU 0 (
            echo Running Trivy scan...
            trivy image --severity HIGH,CRITICAL --ignore-unfixed --no-progress %IMAGE_NAME%:%VERSION% || echo Trivy scan reported issues (continuing)
          ) ELSE (
            echo Trivy not installed - skipping image scan
          )
        '''
      }
    }

    stage('Deploy: Staging') {
      steps {
        bat """
          echo IMAGE_NAME=${IMAGE_NAME} > .env.staging
          echo IMAGE_TAG=${VERSION}>> .env.staging
          docker compose -f docker-compose.staging.yml --env-file .env.staging pull
          docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --force-recreate
          timeout /t 3 >NUL
        """
        script {
          def ok = bat(returnStatus: true, script: 'curl -fsS http://localhost:5000/health >NUL 2>&1') == 0
          if (!ok) { error('Staging health check failed.') }
        }
      }
    }

    stage('Release: Push to Registry') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'DOCKERHUB', usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
          bat """
            echo %DH_TOKEN% | docker login -u %DH_USER% --password-stdin
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
          def ok = bat(returnStatus: true, script: 'curl -fsS http://localhost:5000/health >NUL 2>&1') == 0
          if (!ok) {
            echo 'Health check failed — sending alert (if webhook configured).'
            withCredentials([string(credentialsId: 'SLACK_WEBHOOK', variable: 'SLACK_URL')]) {
              bat '''powershell -NoProfile -Command ^
                "if ($env:SLACK_URL) { Invoke-RestMethod -Method Post -ContentType 'application/json' -Body '{\"text\":\"🚨 devops-flask-app health check FAILED on staging\"}' -Uri $env:SLACK_URL }"
              '''
            }
            error('Monitoring failed.')
          } else {
            echo 'Health check OK.'
          }
        }
      }
    }

    stage('Deploy: Production (optional)') {
      when { expression { return env.DEPLOY_PROD?.trim() == 'true' } }
      steps {
        bat """
          echo IMAGE_NAME=${IMAGE_NAME} > .env.prod
          echo IMAGE_TAG=${VERSION}>> .env.prod
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
