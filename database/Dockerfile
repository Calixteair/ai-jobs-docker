# Image de la base : image officielle MySQL + scripts d'initialisation du projet.
# Construite depuis la racine du dépôt :  docker build -f database/Dockerfile .
#
# Les scripts sont copiés dans l'image (et non montés en volume) pour que
# l'image soit autonome : c'est elle qui sera publiée et déployée sur le VPS.

# 8.4 = version LTS (support long terme), épinglée pour un build reproductible.
FROM mysql:8.4

# Lien vers le dépôt source (affiché par Harbor et les outils OCI)
LABEL org.opencontainers.image.source="https://github.com/Calixteair/ai-jobs-docker"

# Exécutés par ordre alphabétique au premier démarrage, si le volume est vide.
# Les scripts de schéma et d'import sont fournis par la zone data.
COPY database/scripts_initialisation/ /docker-entrypoint-initdb.d/

# Durcissement (Trivy, CRITICAL) : MySQL Shell (mysqlsh, avec son propre Python et certifi) ne sert
# pas ici, et gosu (compilé avec un Go vulnérable) ne sert qu'à passer de root à mysql. En lançant
# directement en mysql, l'entrypoint officiel ne l'appelle plus : on peut le supprimer.
RUN rpm -e mysql-shell && rm -f /usr/local/bin/gosu
USER mysql
