"""Tests d'intégration de l'infrastructure MySQL (zone devops).

Vérifient le conteneur démarré par `make db-up`, sans dépendre du schéma
métier : les tests des données (zone data) viendront s'ajouter dans ce dossier.
"""

import socket
import subprocess

import pytest

pytestmark = pytest.mark.integration

COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f", "compose.test.yaml"]
TEST_PORT = 3307


def in_container(*command: str) -> str:
    result = subprocess.run(
        [*COMPOSE, "exec", "-T", "db", *command], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def mysql(sql: str) -> str:
    """Exécute une requête dans le conteneur avec l'utilisateur applicatif."""
    command = 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -N -e "$0" 2>/dev/null'
    return in_container("sh", "-c", command, sql)


def test_service_is_healthy():
    status = subprocess.run(
        [*COMPOSE, "ps", "db", "--format", "{{.Health}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert status == "healthy"


def test_test_port_is_published_on_localhost():
    with socket.create_connection(("127.0.0.1", TEST_PORT), timeout=5):
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
