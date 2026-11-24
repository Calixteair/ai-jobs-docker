#!/bin/bash
# Sain = synchro du schéma réussie depuis ce démarrage ET serveur joignable en TCP par l'utilisateur
# applicatif (pendant l'init, MySQL tourne sans réseau : sain seulement une fois l'import terminé).
test -f /tmp/ai-jobs-schema-ok &&
  MYSQL_PWD="$MYSQL_PASSWORD" mysqladmin ping -h 127.0.0.1 -u"$MYSQL_USER" --silent
