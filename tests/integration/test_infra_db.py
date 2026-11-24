"""Tests d'intégration de l'infrastructure MySQL (zone devops).

Vérifient le conteneur démarré par `make db-up`, sans dépendre du schéma
métier : les tests des données (zone data) viendront s'ajouter dans ce dossier.
"""

import hashlib
import os
import socket
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f", "compose.test.yaml"]
# Surchargés en CI Jenkins, où MySQL tourne dans le démon Docker « docker »
TEST_HOST = os.environ.get("DB_TEST_HOST", "127.0.0.1")
TEST_PORT = int(os.environ.get("DB_TEST_PORT", "3307"))
INIT_DIR = Path(__file__).resolve().parents[2] / "database" / "scripts_initialisation"


def in_container(*command: str) -> str:
    result = subprocess.run(
        [*COMPOSE, "exec", "-T", "db", *command], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def mysql(sql: str) -> str:
    """Exécute une requête dans le conteneur avec l'utilisateur applicatif.

    Connexion TCP (-h 127.0.0.1), comme le healthcheck : l'emplacement du socket
    Unix dépend de l'environnement (sous Docker-in-Docker, mysqld ne l'ouvre pas
    à l'endroit attendu par le client).
    """
    command = (
        'mysql -h 127.0.0.1 -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"'
        ' -N -e "$0" 2>/dev/null'
    )
    return in_container("sh", "-c", command, sql)


def test_service_is_healthy():
    status = subprocess.run(
        [*COMPOSE, "ps", "db", "--format", "{{.Health}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert status == "healthy"


def test_test_port_is_published():
    with socket.create_connection((TEST_HOST, TEST_PORT), timeout=5):
        pass


def test_mysql_version_is_lts_8_4():
    assert mysql("SELECT VERSION()").startswith("8.4.")


def test_app_user_connects_to_project_database():
    assert mysql("SELECT DATABASE()") == in_container("printenv", "MYSQL_DATABASE")


def test_app_user_has_no_global_privileges():
    grants = mysql("SHOW GRANTS")
    assert "ON *.*" not in grants.replace("GRANT USAGE ON *.*", "")


def test_default_charset_is_utf8mb4():
    assert mysql("SELECT @@character_set_server") == "utf8mb4"


def expected_schema_hash() -> str:
    """Même calcul que database/bin/schema-sync.sh : nom puis « sha256sum » de chaque *.sql."""
    listing = "".join(
        f"{f.name}\n{hashlib.sha256(f.read_bytes()).hexdigest()}  -\n"
        for f in sorted(INIT_DIR.glob("*.sql"))
    )
    return hashlib.sha256(listing.encode()).hexdigest()


def test_schema_sync_recorded_current_scripts():
    # Volume existant (staging, prod) : les scripts d'init y sont rejoués quand ils changent
    assert mysql("SELECT hash FROM _schema_sync WHERE id = 1") == expected_schema_hash()
