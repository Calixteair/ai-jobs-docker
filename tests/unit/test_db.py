"""Tests unitaires de app/db.py (sans MySQL : SQLite en mémoire ou moteur simulé)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from db import DatabaseUnavailable, DbConfig, fetch_dataframe, wait_for_database

VALID_ENV = {
    "DB_HOST": "db",
    "DB_PORT": "3306",
    "MYSQL_USER": "app",
    "MYSQL_PASSWORD": "p@ss:w/rd",
    "MYSQL_DATABASE": "ai_jobs",
}


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def test_config_from_env():
    config = DbConfig.from_env(VALID_ENV)
    assert config == DbConfig("db", 3306, "app", "p@ss:w/rd", "ai_jobs")


def test_config_default_port():
    env = {k: v for k, v in VALID_ENV.items() if k != "DB_PORT"}
    assert DbConfig.from_env(env).port == 3306


def test_config_lists_missing_variables():
    with pytest.raises(ValueError, match="DB_HOST, MYSQL_PASSWORD"):
        DbConfig.from_env({"MYSQL_USER": "app", "MYSQL_DATABASE": "ai_jobs"})


def test_url_escapes_password_and_hides_it():
    url = DbConfig.from_env(VALID_ENV).url()
    assert url.drivername == "mysql+pymysql"
    assert url.password == "p@ss:w/rd"
    assert "p@ss" not in str(url)  # masqué dans les logs


# --------------------------------------------------------------------------- #
# Attente de la base
# --------------------------------------------------------------------------- #


class FlakyEngine:
    """Moteur simulé qui échoue `failures` fois avant de répondre."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def connect(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        return create_engine("sqlite://").connect()


def test_wait_for_database_retries_until_success():
    engine = FlakyEngine(failures=2)
    waits = []
    wait_for_database(engine, attempts=5, delay=1.5, sleep=waits.append)
    assert engine.calls == 3
    assert waits == [1.5, 1.5]


def test_wait_for_database_gives_up():
    engine = FlakyEngine(failures=10)
    with pytest.raises(DatabaseUnavailable, match="3 tentatives"):
        wait_for_database(engine, attempts=3, sleep=lambda _: None)
    assert engine.calls == 3


# --------------------------------------------------------------------------- #
# Requêtes
# --------------------------------------------------------------------------- #


def test_fetch_dataframe_with_parameters():
    engine = create_engine("sqlite://")
    df = fetch_dataframe(engine, "SELECT :a + :b AS total", {"a": 2, "b": 3})
    assert df.loc[0, "total"] == 5


def test_fetch_dataframe_wraps_connection_errors():
    with pytest.raises(DatabaseUnavailable):
        fetch_dataframe(FlakyEngine(failures=1), "SELECT 1")
