// CI/CD du projet, exécutée par Jenkins (jenkins.calixteair.fr) : seul outil de CI du dépôt.
// Le statut « continuous-integration/jenkins/pr-merge » est obligatoire sur dev et main.
// Les conteneurs lancés par le build tournent dans le démon Docker isolé « docker »
// (Docker-in-Docker), pas sur l'agent : MySQL est donc joint via l'hôte « docker ».
pipeline {
  agent { label 'docker' }

  options {
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds(abortPrevious: true)
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timestamps()
  }

  environment {
    DB_TEST_BIND = '0.0.0.0'
    DB_TEST_HOST = 'docker'
  }

  stages {
    stage('Lint (ruff)') {
      steps {
        sh 'make lint'
      }
    }

    stage('Tests unitaires') {
      steps {
        sh 'make test'
      }
      post {
        always { junit 'report.xml' }
      }
    }

    stage("Tests d'intégration MySQL") {
      steps {
        // Un port par exécuteur : deux branches peuvent tourner en parallèle sur le même démon
        sh '''
          export DB_TEST_PORT=$((3307 + EXECUTOR_NUMBER))
          cp .env.example .env
          make db-up
          make test-int
          make test-persistence
        '''
      }
      post {
        failure { sh 'docker compose -f compose.yaml -f compose.test.yaml logs db || true' }
        always {
          junit allowEmptyResults: true, testResults: 'report-integration.xml'
          sh 'make db-reset || true'
        }
      }
    }

    stage('Scan de secrets (gitleaks)') {
      steps {
        // Chemin identique dans l'agent et dans dind : le montage $PWD fonctionne
        sh 'docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:v8.21.2 detect --source /repo --redact --verbose'
      }
    }
  }
}
