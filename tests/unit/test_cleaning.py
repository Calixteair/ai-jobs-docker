"""Tests du nettoyage (scripts/cleaning.py, issue #13)."""

from pathlib import Path

import cleaning
import pandas as pd
import pytest


@pytest.fixture
def raw() -> pd.DataFrame:
    """Les 10 premières offres du vrai dataset, à modifier dans chaque test."""
    return pd.read_csv(cleaning.DEFAULT_CSV, nrows=10)


@pytest.fixture
def journal() -> cleaning.Journal:
    return cleaning.Journal()


# --------------------------------------------------------------------------- #
# Garde-fous
# --------------------------------------------------------------------------- #


def test_valid_data_has_no_integrity_problem(raw):
    assert cleaning.integrity_problems(raw) == []


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("city", None, "manquante"),
        ("job_id", "AIJOB0002", "job_id en double"),
        ("remote_work", "Remote", "inconnue(s) dans remote_work"),
        ("is_senior", 0, "is_senior incohérent"),
        ("is_remote_friendly", 0, "is_remote_friendly incohérent"),
        ("salary_tier", "Elite (>$300k)", "salary_tier incohérent"),
        ("required_skills", "Python|sql|SQL", "plusieurs façons"),
    ],
)
def test_integrity_problems_detect_each_anomaly(raw, column, value, message):
    # Pour un indicateur, on part d'une ligne où il vaut 1 pour le passer à 0
    row = raw.index[raw[column] == 1][0] if column.startswith("is_") else 0
    raw[column] = raw[column].astype(object)
    raw.loc[row, column] = value
    problems = cleaning.integrity_problems(raw)
    assert any(message in problem for problem in problems), problems


def test_check_integrity_raises_and_logs(raw, journal):
    cleaning.check_integrity(raw, journal)
    assert journal.steps[0].rows == len(raw)

    raw.loc[0, "remote_work"] = "Remote"
    with pytest.raises(cleaning.CleaningError, match="remote_work"):
        cleaning.check_integrity(raw, cleaning.Journal())


@pytest.mark.parametrize(
    ("salary", "tier"),
    [
        (90_000, "Entry (<$100k)"),
        (100_000, "Entry (<$100k)"),  # borne haute incluse
        (100_001, "Mid ($100-150k)"),
        (300_000, "Senior ($200-300k)"),
        (300_001, "Elite (>$300k)"),
    ],
)
def test_expected_salary_tier_limits(salary, tier):
    assert cleaning.expected_salary_tier(pd.Series([salary])).iloc[0] == tier


def test_skill_spelling_variants():
    assert cleaning.skill_spelling_variants(pd.Series(["SQL|Git", " sql |Python"])) == ["SQL, sql"]
    assert cleaning.skill_spelling_variants(pd.Series(["SQL|Git", "SQL"])) == []


# --------------------------------------------------------------------------- #
# Transformations
# --------------------------------------------------------------------------- #


def test_strip_text_counts_changed_rows(raw, journal):
    raw.loc[0, "city"] = "  Boston "
    raw.loc[0, "country"] = "USA "
    raw.loc[1, "industry"] = " Finance"

    out = cleaning.strip_text(raw, journal)

    assert out.loc[0, "city"] == "Boston"
    assert journal.steps[-1].rows == 2  # deux lignes touchées, trois cellules


def test_convert_types(raw, journal):
    out = cleaning.convert_types(raw, journal)

    assert out["annual_salary_usd"].dtype.kind == "i"
    assert out["is_llm_role"].dtype == bool
    assert len(journal.steps) == 2


def test_convert_types_rejects_decimal_salary(raw, journal):
    raw.loc[0, "annual_salary_usd"] = 239_000.5
    with pytest.raises(cleaning.CleaningError, match="non entières"):
        cleaning.convert_types(raw, journal)


def test_convert_types_rejects_invalid_flag(raw, journal):
    raw.loc[0, "is_llm_role"] = 2
    with pytest.raises(cleaning.CleaningError, match="is_llm_role"):
        cleaning.convert_types(raw, journal)


@pytest.mark.parametrize(
    ("raw_skills", "expected"),
    [
        ("Python|SQL|Cloud", ["Python", "SQL", "Cloud"]),
        ("SQL|Python|SQL", ["SQL", "Python"]),  # C2 : première occurrence gardée
        (" Python | SQL ", ["Python", "SQL"]),  # C4 : espaces retirés
        ("Python||SQL|", ["Python", "SQL"]),  # éléments vides ignorés
        ("CI/CD|Cloud (AWS/GCP/Azure)", ["CI/CD", "Cloud (AWS/GCP/Azure)"]),  # C1
        ("Python", ["Python"]),
    ],
)
def test_parse_skills(raw_skills, expected):
    assert cleaning.parse_skills(raw_skills) == expected


def test_parse_skills_is_idempotent():
    once = cleaning.parse_skills("SQL| Python|SQL||Git")
    assert cleaning.parse_skills("|".join(once)) == once


def test_clean_skills_logs_affected_rows(raw, journal):
    out = cleaning.clean_skills(raw, journal)

    assert out.loc[3, "required_skills"].count("SQL") == 1  # AIJOB0004
    assert journal.steps[-1].rows == int(
        (raw["required_skills"].str.split("|").map(lambda s: len(s) != len(set(s)))).sum()
    )
    assert "AIJOB0004" in journal.steps[-1].before


def test_add_derived_columns(raw, journal):
    df = cleaning.convert_types(raw, journal)
    out = cleaning.add_derived_columns(df, journal)

    first = out.iloc[0]
    assert first["experience_rank"] == cleaning.EXPERIENCE_RANK[first["experience_level"]]
    assert first["posting_period"] == f"{first['posting_year']}-{first['posting_month']:02d}"
    assert (out["salary_above_range"] == (out["annual_salary_usd"] > out["salary_max_usd"])).all()


def test_build_tables_and_constraints(raw, journal):
    df = cleaning.clean_skills(raw, journal)
    tables = cleaning.build_tables(df)

    assert "required_skills" not in tables["jobs"].columns
    assert tables["skills"]["skill_id"].tolist() == list(range(1, len(tables["skills"]) + 1))
    assert len(tables["job_skills"]) == df["required_skills"].str.len().sum()
    assert cleaning.table_problems(tables) == []


def test_table_problems_detect_broken_keys(raw, journal):
    tables = cleaning.build_tables(cleaning.clean_skills(raw, journal))
    tables["job_skills"] = pd.concat(
        [tables["job_skills"], pd.DataFrame({"job_id": ["AIJOB9999"], "skill_id": [999]})]
    )
    problems = cleaning.table_problems(tables)

    assert any("offre absente" in p for p in problems)
    assert any("compétence absente" in p for p in problems)


def test_to_csv_text_writes_booleans_as_integers():
    text = cleaning.to_csv_text(pd.DataFrame({"job_id": ["A"], "is_llm_role": [True]}))
    assert text == "job_id,is_llm_role\nA,1\n"


# --------------------------------------------------------------------------- #
# Pipeline complet sur le vrai dataset
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def tables() -> dict[str, pd.DataFrame]:
    tables, _ = cleaning.clean(pd.read_csv(cleaning.DEFAULT_CSV))
    return tables


def test_real_dataset_volumes(tables):
    assert {name: len(t) for name, t in tables.items()} == {
        "jobs": 1500,
        "skills": 93,
        "job_skills": 9428,
    }


def test_cleaning_preserves_salaries(tables):
    raw = pd.read_csv(cleaning.DEFAULT_CSV)
    assert tables["jobs"]["annual_salary_usd"].sum() == raw["annual_salary_usd"].sum()
    assert int(tables["jobs"]["salary_above_range"].sum()) == 288


def test_run_is_idempotent(tmp_path: Path):
    journal_path = tmp_path / "journal.md"
    cleaning.run(cleaning.DEFAULT_CSV, tmp_path / "out", journal_path)
    first = {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()}
    first_journal = journal_path.read_bytes()

    cleaning.run(cleaning.DEFAULT_CSV, tmp_path / "out", journal_path)

    assert {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()} == first
    assert journal_path.read_bytes() == first_journal
    assert sorted(first) == ["job_skills.csv", "jobs.csv", "skills.csv"]


def test_committed_journal_is_up_to_date(tmp_path: Path):
    """Le journal versionné doit correspondre au CSV : sinon relancer le script."""
    journal_path = tmp_path / "journal.md"
    cleaning.run(cleaning.DEFAULT_CSV, tmp_path / "out", journal_path)
    generated = journal_path.read_text(encoding="utf-8").replace(
        cleaning.display_path(cleaning.DEFAULT_CSV), "data/ai_jobs_market_2025_2026.csv"
    )
    assert cleaning.DEFAULT_JOURNAL.read_text(encoding="utf-8") == generated
