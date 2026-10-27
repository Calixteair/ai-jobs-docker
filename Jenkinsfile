// CI/CD du projet, exécutée par Jenkins (jenkins.calixteair.fr) : seul outil de CI du dépôt.
// Le statut « continuous-integration/jenkins/pr-merge » est obligatoire sur dev et main.
// Les conteneurs lancés par le build tournent dans le démon Docker isolé « docker »
// (Docker-in-Docker), pas sur l'agent : MySQL est donc joint via l'hôte « docker ».
//
// Livraison (après les tests) :
//   dev  → images :sha-<commit> et :staging sur GHCR → déploiement staging → contrôle de l'URL
//   main → images :sha-<commit> → approbation manuelle (jenkins-admins) → :prod → déploiement prod
// Les PR et les autres branches s'arrêtent aux tests.
pipeline {
  agent { label 'docker' }

  options {
    timeout(time: 60, unit: 'MINUTES')
    // Un nouveau commit annule le build en cours d'une PR, jamais un déploiement de dev ou main
    disableConcurrentBuilds(abortPrevious: !(env.BRANCH_NAME in ['dev', 'main']))
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timestamps()
  }

  environment {
    DB_TEST_BIND = '0.0.0.0'
    DB_TEST_HOST = 'docker'
    REGISTRY = 'ghcr.io/calixteair'
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

    stage('Smoke tests T1 à T5') {
      steps {
        // Stack complète (app + db) construite depuis zéro, puis down -v.
        // Port et nom de projet propres à l'exécuteur : deux builds peuvent tourner en parallèle.
        sh '''
          export SMOKE_HOST=docker
          export APP_PORT=$((8601 + EXECUTOR_NUMBER))
          export COMPOSE_PROJECT_NAME="ai-jobs-smoke-$EXECUTOR_NUMBER"
          cp .env.example .env
          make smoke
        '''
      }
    }

    stage('Scan de secrets (gitleaks)') {
      steps {
        // Chemin identique dans l'agent et dans dind : le montage $PWD fonctionne
        sh 'docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:v8.21.2 detect --source /repo --redact --verbose'
      }
    }

    stage('Publication des images (GHCR)') {
      when { anyOf { branch 'dev'; branch 'main' } }
      steps {
        withCredentials([usernamePassword(credentialsId: 'ghcr-push',
                                          usernameVariable: 'GHCR_USER', passwordVariable: 'GHCR_TOKEN')]) {
          // Identifiants Docker propres au build (pas dans le ~/.docker partagé de l'agent)
          sh '''
            export DOCKER_CONFIG="$WORKSPACE@tmp/docker-ghcr"
            echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
            SHA=sha-$(git rev-parse --short=12 HEAD)
            docker build -t "$REGISTRY/ai-jobs-docker-app:$SHA" .
            docker build -t "$REGISTRY/ai-jobs-docker-db:$SHA" -f database/Dockerfile .
            docker push "$REGISTRY/ai-jobs-docker-app:$SHA"
            docker push "$REGISTRY/ai-jobs-docker-db:$SHA"
          '''
        }
      }
      post { always { sh 'rm -rf "$WORKSPACE@tmp/docker-ghcr"' } }
    }

    stage('Déploiement staging') {
      when { branch 'dev' }
      steps { deployTo('staging', 'https://ai-jobs-staging.calixteair.fr') }
    }

    stage('Approbation production') {
      when { branch 'main' }
      steps {
        timeout(time: 30, unit: 'MINUTES') {
          input message: 'Déployer ce commit en production ?', ok: 'Déployer', submitter: 'jenkins-admins'
        }
      }
    }

    stage('Déploiement production') {
      when { branch 'main' }
      steps { deployTo('prod', 'https://ai-jobs.calixteair.fr') }
    }
  }
}

// Étiquette les images du commit pour l'environnement (:staging ou :prod), puis
// déclenche le redéploiement sur le VPS avec la clé SSH propre à cet environnement.
def deployTo(String envName, String url) {
  withCredentials([usernamePassword(credentialsId: 'ghcr-push',
                                    usernameVariable: 'GHCR_USER', passwordVariable: 'GHCR_TOKEN')]) {
    sh """
      export DOCKER_CONFIG="\$WORKSPACE@tmp/docker-ghcr"
      trap 'rm -rf "\$DOCKER_CONFIG"' EXIT
      echo "\$GHCR_TOKEN" | docker login ghcr.io -u "\$GHCR_USER" --password-stdin
      SHA=sha-\$(git rev-parse --short=12 HEAD)
      for image in ai-jobs-docker-app ai-jobs-docker-db; do
        docker tag "\$REGISTRY/\$image:\$SHA" "\$REGISTRY/\$image:${envName}"
        docker push "\$REGISTRY/\$image:${envName}"
      done
    """
  }
  def secrets = [file(credentialsId: 'vps-known-hosts', variable: 'KNOWN_HOSTS')]
  if (envName == 'staging') {
    // Le staging est protégé par une access list NPM (basic auth)
    secrets << usernameColonPassword(credentialsId: 'ai-jobs-staging-access', variable: 'BASIC_AUTH')
  }
  withCredentials(secrets) {
    sshagent(credentials: ["ci-ai-jobs-${envName}"]) {
      withEnv(["APP_URL=${url}"]) {
        sh "deploy/deploy.sh ${envName}"
      }
    }
  }
}
