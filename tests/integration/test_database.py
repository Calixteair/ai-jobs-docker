"""Tests d'intégration : la base MySQL importée correspond aux données nettoyées.

Prérequis : `make db-up` (lancé automatiquement par `make test-int`).
"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from db import fetch_dataframe

pytestmark = pytest.mark.integration

QUERIES_FILE = Path(__file__).resolve().parents[2] / "database" / "requetes_dashboard.sql"


def scalar(engine, sql: str):
    return fetch_dataframe(engine, sql).iat[0, 0]


def dashboard_queries() -> list[str]:
    """Découpe requetes_dashboard.sql en requêtes, sans les lignes de commentaire."""
    lines = [line for line in QUERIES_FILE.read_text().splitlines() if not line.startswith("--")]
    return [q.strip() for q in "\n".join(lines).split(";") if q.strip()]


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("table", ["jobs", "skills", "job_skills"])
def test_row_counts_match_cleaned_data(engine, expected, table):
    assert scalar(engine, f"SELECT COUNT(*) FROM {table}") == len(expected[table])


def test_every_job_has_skills(engine):
    orphans = scalar(
        engine,
        "SELECT COUNT(*) FROM jobs j "
        "WHERE NOT EXISTS (SELECT 1 FROM job_skills js WHERE js.job_id = j.job_id)",
    )
    assert orphans == 0


def test_job_row_is_identical(engine, expected):
    row = fetch_dataframe(engine, "SELECT * FROM jobs WHERE job_id = 'AIJOB0004'").iloc[0]
    source = expected["jobs"].set_index("job_id").loc["AIJOB0004"]
    for column in ["job_title", "country", "remote_work", "annual_salary_usd", "posting_period"]:
        assert row[column] == source[column], column


def test_duplicated_skills_were_removed(engine):
    sql = (
        "SELECT COUNT(*) FROM job_skills js JOIN skills s USING (skill_id) "
        "WHERE js.job_id = 'AIJOB0004' AND s.name = 'SQL'"
    )
    assert scalar(engine, sql) == 1


# --------------------------------------------------------------------------- #
# Requêtes du dashboard
# --------------------------------------------------------------------------- #


def test_all_dashboard_queries_run(engine):
    queries = dashboard_queries()
    assert len(queries) >= 5
    for sql in queries:
        assert not fetch_dataframe(engine, sql).empty, sql[:60]


def test_kpis_match_pandas(engine, expected):
    jobs = expected["jobs"]
    kpis = fetch_dataframe(engine, dashboard_queries()[0]).iloc[0]
    assert kpis["nb_offres"] == len(jobs)
    assert kpis["salaire_moyen"] == round(jobs["annual_salary_usd"].mean())
    assert float(kpis["demande_moyenne"]) == round(jobs["demand_score"].mean(), 1)


def test_median_matches_pandas(engine, expected):
    median = scalar(engine, dashboard_queries()[1])
    assert median == expected["jobs"]["annual_salary_usd"].median()


# --------------------------------------------------------------------------- #
# Contraintes du schéma
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("column", "value"),
    [("remote_work", "'Remote-ish'"), ("demand_score", "150"), ("posting_month", "13")],
)
def test_schema_rejects_invalid_values(engine, column, value):
    with engine.connect() as connection, pytest.raises(DBAPIError):
        connection.execute(text(f"UPDATE jobs SET {column} = {value} WHERE job_id = 'AIJOB0001'"))
        connection.rollback()


def test_foreign_key_rejects_unknown_job(engine):
    with engine.connect() as connection, pytest.raises(DBAPIError):
        connection.execute(text("INSERT INTO job_skills VALUES ('AIJOB9999', 1)"))
        connection.rollback()
