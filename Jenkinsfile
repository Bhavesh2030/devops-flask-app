pipeline {
  agent any
  stages {
    stage('Build') {
      steps {
        sh 'docker build -t flask-app .'
      }
    }
    stage('Test') {
      steps {
        sh 'pytest --maxfail=1 --disable-warnings -q'
      }
    }
    stage('Code Quality') {
      steps {
        sh 'pylint app.py || true'
      }
    }
    stage('Security') {
      steps {
        sh 'bandit -r . || true'
      }
    }
  }
}
