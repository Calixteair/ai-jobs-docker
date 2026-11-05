// CI/CD du projet, exécutée par Jenkins (jenkins.calixteair.fr) : seul outil de CI du dépôt.
// Le statut « continuous-integration/jenkins/pr-merge » est obligatoire sur dev et main.
// Les conteneurs lancés par le build tournent dans le démon Docker isolé « docker »
// (Docker-in-Docker), pas sur l'agent : MySQL est donc joint via l'hôte « docker ».
// Étapes communes (images, Trivy, gitleaks, Harbor, déploiement) : bibliothèque jenkins-lib.
//
// Livraison (après les tests), images sur Harbor (registry.calixteair.fr/ai-jobs/ai-jobs) :
//   dev         → :<préfixe>-sha-<commit> et :<préfixe>-staging → déploiement staging → contrôle de l'URL
//   main        → :<préfixe>-sha-<commit> et :<préfixe>-latest, sans déploiement
//   tag vX.Y.Z  → :vX.Y.Z-<préfixe> (immuables) → déploiement prod par stack-sync, qui vérifie sur le VPS
//                 que le tag est signé par Calixteair (un tag non signé est refusé)
// Préfixes : app (Streamlit) et db (MySQL + scripts d'initialisation).
// Les PR s'arrêtent aux tests. Elles sont construites dans un dossier Jenkins à part (groupes-pr/),
// sur un autre agent, sans aucun identifiant : seuls dev, main et les tags ont accès à Harbor et aux clés.
// Ce fichier, le Makefile, deploy/ et scripts/ sont sous CODEOWNERS (review de Calixteair).
@Library('calixteair@v1') _
import fr.calixteair.ci.Refs

// Identifiants lus dans OpenBao (AppRole des projets de groupe : secret/cicd/groupes/* seulement)
def BAO = [harbor: 'cicd/groupes/harbor/ai-jobs', staging: 'cicd/groupes/ai-jobs/staging-deploy',
           stagingAccess: 'cicd/groupes/ai-jobs/staging-access', prod: 'cicd/groupes/ai-jobs/deploy']
def IMAGES = [[name: 'ai-jobs', tagPrefix: 'app', context: '.', dockerfile: 'Dockerfile'],
              [name: 'ai-jobs', tagPrefix: 'db', context: '.', dockerfile: 'database/Dockerfile']]
def built = []

pipeline {
  agent { label 'docker' }

  options {
    timeout(time: 60, unit: 'MINUTES')
    // Un nouveau commit annule le build en cours d'une PR, jamais un déploiement de dev ou main
    disableConcurrentBuilds(abortPrevious: !(env.BRANCH_NAME in ['dev', 'main']) && !Refs.isReleaseTag(env.TAG_NAME))
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timestamps()
  }

  environment {
    REGISTRY = 'registry.calixteair.fr/ai-jobs'
  }

  stages {
    stage('Tests') {
      environment {
        DB_TEST_BIND = '0.0.0.0'
        DB_TEST_HOST = 'docker'
        // Si plusieurs exécuteurs partagent le démon dind : un nom de projet Compose par
        // exécuteur évite que deux builds simultanés se disputent conteneurs et volumes.
        COMPOSE_PROJECT_NAME = "ai-jobs-ci-${env.EXECUTOR_NUMBER}"
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
          steps { scanSecrets() }
        }
      }
    }

    stage('Images + Trivy') {
      when { expression { livraison() } }
      steps {
        script {
          built = IMAGES.collect { img ->
            def tags = buildImage(img)
            scanImage(tags.sha)
            tags
          }
        }
      }
    }

    stage('Publication (Harbor)') {
      when { expression { livraison() } }
      steps { script { built.each { publish(it, BAO.harbor) } } }
    }

    stage('Déploiement staging') {
      when { branch 'dev' }
      steps {
        deployStack(stack: 'ai-jobs-staging', secret: BAO.staging, basicAuth: BAO.stagingAccess,
                    url: 'https://ai-jobs-staging.calixteair.fr/_stcore/health', healthAttempts: 15)
      }
    }

    stage('Déploiement production') {
      when { expression { Refs.isReleaseTag(env.TAG_NAME) } }
      steps {
        deployStack(stack: 'ai-jobs', ref: env.TAG_NAME, secret: BAO.prod,
                    url: 'https://ai-jobs.calixteair.fr/_stcore/health', healthAttempts: 15)
      }
    }
  }
}

// dev, main et les tags vX.Y.Z publient ; les autres branches s'arrêtent aux tests
boolean livraison() {
  return env.BRANCH_NAME in ['dev', 'main'] || Refs.isReleaseTag(env.TAG_NAME)
}

// Image du commit (:<préfixe>-sha-<commit>) plus, selon la référence construite :
// tag vX.Y.Z → :vX.Y.Z-<préfixe> ; dev → :<préfixe>-staging ; main → :<préfixe>-latest
void publish(Map image, String secret) {
  String other = Refs.isReleaseTag(env.TAG_NAME) ? Refs.releaseRef(image.latest, env.TAG_NAME)
               : (env.BRANCH_NAME == 'dev' ? image.latest.replaceAll(/-latest$/, '-staging') : null)
  Map tags = image
  if (other) {
    sh "docker tag '${Refs.checkImageRef(image.sha)}' '${Refs.checkImageRef(other)}'"
    tags = [sha: image.sha, latest: other]
  }
  echo "image publiée : ${pushImage(tags, [secret: secret])}"
}
