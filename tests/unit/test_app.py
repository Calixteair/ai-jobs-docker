"""Tests de l'interface (app/app.py) avec streamlit.testing, sans MySQL."""

from pathlib import Path

import db
import pytest
import streamlit as st
from sqlalchemy import create_engine
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[2] / "app" / "app.py")
CONFIG = db.DbConfig(
    host="db",
    port=3306,
    database="ai_jobs",
    user="ai_jobs_app",
    password="secret-de-test",
    connect_retries=1,
    retry_delay_s=0,
)


@pytest.fixture(autouse=True)
def clear_connection_cache():
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def run_app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30).run()


def test_connected_app_shows_status(monkeypatch):
    engine = create_engine("sqlite://")
    engine.connect().close()  # renseigne la version du serveur
    monkeypatch.setattr(db, "connect", lambda: (engine, CONFIG))

    at = run_app()

    assert not at.exception
    assert "Base connectée" in at.sidebar.success[0].value
    assert CONFIG.password not in str(at.sidebar)


def test_unavailable_database_shows_message_and_retry(monkeypatch):
    def unavailable():
        raise db.DatabaseUnavailable("La base n'a pas répondu après 1 tentative(s).")

    monkeypatch.setattr(db, "connect", unavailable)

    at = run_app()

    assert not at.exception
    assert "Base de données injoignable" in at.error[0].value
    assert at.button[0].label == "Réessayer"


def test_retry_reconnects_once_database_is_back(monkeypatch):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise db.DatabaseUnavailable("indisponible")
        return create_engine("sqlite://"), CONFIG

    monkeypatch.setattr(db, "connect", flaky)

    at = run_app()
    at.button[0].click().run()

    assert not at.error
    assert "Base connectée" in at.sidebar.success[0].value


def test_missing_configuration_is_explained(monkeypatch):
    def misconfigured():
        raise db.DatabaseConfigError("Variable(s) d'environnement manquante(s) : DB_USER.")

    monkeypatch.setattr(db, "connect", misconfigured)

    at = run_app()

    assert not at.exception
    assert "Configuration incomplète" in at.error[0].value
