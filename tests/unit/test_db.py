"""Tests de la connexion à la base (app/db.py), sans MySQL."""

import db
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

ENV = {
    "DB_NAME": "ai_jobs",
    "DB_USER": "ai_jobs_app",
    "DB_PASSWORD": "p@ss/w:rd",
    "DB_HOST": "db",
    "DB_PORT": "3306",
}


class FlakyEngine:
    """Faux moteur dont les `fail` premières connexions échouent."""

    def __init__(self, fail: int):
        self.fail = fail
        self.attempts = 0
        self.sqlite = create_engine("sqlite://")

    def connect(self):
        self.attempts += 1
        if self.attempts <= self.fail:
            raise OperationalError("SELECT 1", {}, ConnectionRefusedError("refusée"))
        return self.sqlite.connect()


def test_load_config_reads_environment():
    config = db.load_config(ENV)

    assert (config.host, config.port, config.database) == ("db", 3306, "ai_jobs")
    assert config.connect_retries == 5


def test_load_config_defaults_to_compose_service_name():
    env = {k: v for k, v in ENV.items() if k not in ("DB_HOST", "DB_PORT")}

    config = db.load_config(env)

    assert (config.host, config.port) == ("db", 3306)


def test_load_config_names_missing_variables():
    env = {**ENV, "DB_PASSWORD": ""}
    del env["DB_USER"]

    with pytest.raises(db.DatabaseConfigError, match="DB_USER, DB_PASSWORD"):
        db.load_config(env)


def test_load_config_rejects_non_numeric_port():
    with pytest.raises(db.DatabaseConfigError, match="numérique"):
        db.load_config({**ENV, "DB_PORT": "abc"})


def test_password_never_displayed():
    config = db.load_config(ENV)

    assert ENV["DB_PASSWORD"] not in config.target
    assert ENV["DB_PASSWORD"] not in str(db.build_url(config))


def test_url_escapes_special_characters_in_password():
    url = db.build_url(db.load_config(ENV))

    assert url.drivername == "mysql+pymysql"
    assert url.password == ENV["DB_PASSWORD"]
    assert "p%40ss%2Fw%3Ard" in url.render_as_string(hide_password=False)


def test_wait_for_db_retries_until_success():
    engine = FlakyEngine(fail=2)
    pauses = []

    db.wait_for_db(engine, retries=5, delay_s=2, sleep=pauses.append)

    assert engine.attempts == 3
    assert pauses == [2, 2]


def test_wait_for_db_gives_up_after_max_retries(caplog):
    engine = FlakyEngine(fail=10)

    with pytest.raises(db.DatabaseUnavailable, match="3 tentative"):
        db.wait_for_db(engine, retries=3, delay_s=0, sleep=lambda _: None)

    assert engine.attempts == 3
    assert "tentative 3/3" in caplog.text


def test_server_version_is_read_after_connection():
    engine = create_engine("sqlite://")
    assert db.server_version(engine) == "inconnue"

    engine.connect().close()

    assert db.server_version(engine).count(".") == 2
