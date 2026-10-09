"""Tests unitaires du nettoyage (scripts/cleaning.py)."""

from pathlib import Path

import pandas as pd
import pytest

import cleaning
from cleaning import Journal

RAW_CSV = Path(__file__).resolve().parents[2] / "data" / "ai_jobs_market_2025_2026.csv"


def make_row(**overrides) -> dict:
    """Une offre valide minimale, modifiable champ par champ."""
    row = {
        "job_id": "AIJOB0001",
        "job_title": "LLM Engineer",
        "job_category": "AI Engineering",
        "experience_level": "Senior (6-9 yrs)",
        "years_of_experience": 7,
        "education_required": "Master's",
        "annual_salary_usd": 250000.0,
        "salary_min_usd": 160000,
        "salary_max_usd": 300000,
        "city": "Paris",
        "country": "France",
        "remote_work": "Hybrid",
        "company_size": "Startup (1-50)",
        "industry": "Technology",
        "required_skills": "Python|SQL",
        "ai_salary_premium_pct": 10.0,
        "demand_score": 90,
        "demand_growth_yoy_pct": 20.0,
        "benefits_score_10": 8.0,
        "posting_year": 2026,
        "posting_month": 1,
        "is_senior": 1,
        "is_remote_friendly": 1,
        "is_llm_role": 1,
        "salary_tier": "Senior ($200-300k)",
    }
    row.update(overrides)
    return row


def make_df(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows) or [make_row()])


# --------------------------------------------------------------------------- #
# parse_skills (D1)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Python|SQL", ["Python", "SQL"]),
        ("SQL|Python|SQL", ["SQL", "Python"]),
        (" Python | SQL ", ["Python", "SQL"]),
        ("Python||SQL", ["Python", "SQL"]),
        ("Cloud|Python|Leadership|Enterprise Architecture|Cloud",
         ["Cloud", "Python", "Leadership", "Enterprise Architecture"]),
    ],
)  # fmt: skip
def test_parse_skills(raw, expected):
    assert cleaning.parse_skills(raw) == expected


# --------------------------------------------------------------------------- #
# check_integrity (D8)
# --------------------------------------------------------------------------- #


def test_check_integrity_accepts_valid_data():
    cleaning.check_integrity(make_df())


def test_check_integrity_rejects_missing_values():
    with pytest.raises(ValueError, match="manquante"):
        cleaning.check_integrity(make_df(make_row(city=None)))


def test_check_integrity_rejects_duplicated_ids():
    with pytest.raises(ValueError, match="double"):
        cleaning.check_integrity(make_df(make_row(), make_row()))


def test_check_integrity_rejects_unknown_category():
    with pytest.raises(ValueError, match="remote_work"):
        cleaning.check_integrity(make_df(make_row(remote_work="Remote-ish")))


# --------------------------------------------------------------------------- #
# Transformations
# --------------------------------------------------------------------------- #


def test_strip_text_columns_counts_changes():
    journal = Journal()
    out = cleaning.strip_text_columns(make_df(make_row(city=" Paris ")), journal)
    assert out.loc[0, "city"] == "Paris"
    assert journal.entries[0][1] == 1


def test_convert_types():
    out = cleaning.convert_types(make_df(), Journal())
    assert out["annual_salary_usd"].dtype.kind == "i"
    assert out["is_senior"].dtype == bool


def test_convert_types_rejects_decimal_salary():
    with pytest.raises(ValueError, match="non entières"):
        cleaning.convert_types(make_df(make_row(annual_salary_usd=1000.5)), Journal())


def test_convert_types_rejects_invalid_flag():
    with pytest.raises(ValueError, match="is_llm_role"):
        cleaning.convert_types(make_df(make_row(is_llm_role=2)), Journal())


def test_add_derived_columns():
    df = make_df(
        make_row(job_id="AIJOB0001", annual_salary_usd=350000, posting_month=3),
        make_row(job_id="AIJOB0002", experience_level="Entry (0-2 yrs)"),
    )
    out = cleaning.add_derived_columns(df, Journal())
    assert out["experience_rank"].tolist() == [3, 1]
    assert out["posting_period"].tolist() == ["2026-03", "2026-01"]
    assert out["salary_above_range"].tolist() == [True, False]


def test_deduplicate_skills_reports_affected_rows():
    journal = Journal()
    df = make_df(
        make_row(job_id="AIJOB0001", required_skills="SQL|Python|SQL"),
        make_row(job_id="AIJOB0002", required_skills="Python|Git"),
    )
    out = cleaning.deduplicate_skills(df, journal)
    assert out.loc[0, "required_skills"] == ["SQL", "Python"]
    assert journal.entries[-1][1] == 1


# --------------------------------------------------------------------------- #
# Normalisation (D9)
# --------------------------------------------------------------------------- #


def test_build_tables():
    df = make_df(
        make_row(job_id="AIJOB0001", required_skills=["Python", "SQL"]),
        make_row(job_id="AIJOB0002", required_skills=["SQL"]),
    )
    jobs, skills, job_skills = cleaning.build_tables(df)

    assert "required_skills" not in jobs.columns
    assert skills.to_dict("list") == {"skill_id": [1, 2], "name": ["Python", "SQL"]}
    assert job_skills.values.tolist() == [["AIJOB0001", 1], ["AIJOB0001", 2], ["AIJOB0002", 2]]


# --------------------------------------------------------------------------- #
# Pipeline complet sur le vrai dataset
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def tables(tmp_path_factory):
    return cleaning.run(RAW_CSV, tmp_path_factory.mktemp("processed"))


def test_run_on_real_dataset(tables):
    assert len(tables["jobs"]) == 1500
    assert len(tables["skills"]) == 93
    assert not tables["job_skills"].duplicated().any()


def test_run_keeps_every_job_linked(tables):
    assert set(tables["job_skills"]["job_id"]) == set(tables["jobs"]["job_id"])


def test_run_preserves_salary_statistics(tables):
    raw = pd.read_csv(RAW_CSV)
    assert tables["jobs"]["annual_salary_usd"].mean() == pytest.approx(
        raw["annual_salary_usd"].mean()
    )


def test_run_writes_files(tmp_path):
    cleaning.run(RAW_CSV, tmp_path)
    expected = {"jobs.csv", "skills.csv", "job_skills.csv", "journal_nettoyage.md"}
    assert expected <= {p.name for p in tmp_path.iterdir()}
    assert pd.read_csv(tmp_path / "jobs.csv")["is_senior"].isin([0, 1]).all()
