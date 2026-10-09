"""Tests du script d'exploration du dataset (scripts/explore_dataset.py)."""

from pathlib import Path

import explore_dataset as explore
import pandas as pd
import pytest


@pytest.fixture
def sample() -> pd.DataFrame:
    """Les 5 premières offres du vrai dataset, à modifier dans chaque test."""
    return pd.read_csv(explore.DEFAULT_CSV, nrows=5)


def write_and_load(df: pd.DataFrame, tmp_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    path = tmp_path / "jobs.csv"
    df.to_csv(path, index=False)
    typed, raw = explore.load(path)
    return typed, raw, path


def test_skill_set_ignores_order_and_repetitions():
    skills = pd.Series(["SQL|Python|SQL", "Python|SQL"])
    assert explore.skill_set(skills).tolist() == ["Python|SQL", "Python|SQL"]


def test_missing_checks_detect_blank_and_disguised_values(sample, tmp_path):
    sample.loc[0, "city"] = "N/A"
    sample.loc[1, "country"] = "  "
    sample.loc[2, "industry"] = "unknown"
    sample.loc[3, "annual_salary_usd"] = 0
    sample.loc[4, "required_skills"] = "Python||SQL"
    typed, raw, path = write_and_load(sample, tmp_path)

    checks = explore.missing_checks(typed, raw, explore.count_malformed_lines(path))

    assert checks["nan"] == 1  # « N/A » est converti en NaN par pandas
    assert checks["blank"] == 1
    assert checks["disguised"] == 2  # « N/A » et « unknown »
    assert checks["non_positive"] == 1
    assert checks["empty_skill"] == 1
    assert checks["malformed"] == 0


def test_count_malformed_lines(tmp_path):
    path = tmp_path / "jobs.csv"
    header = ",".join(f"c{i}" for i in range(explore.EXPECTED_COLUMNS))
    path.write_text(f"{header}\n{'x,' * 24}x\nligne,trop,courte\n")
    assert explore.count_malformed_lines(path) == 1


def test_duplicate_checks_detect_same_offer_under_two_ids(sample):
    copy = sample.iloc[[0]].assign(job_id="AIJOB9999")
    checks = explore.duplicate_checks(pd.concat([sample, copy], ignore_index=True))

    assert checks["job_id"] == 0
    assert checks["full_row"] == 0
    assert checks["without_id"] == 1


def test_duplicate_checks_detect_reordered_skills_and_label_variants(sample):
    sample.loc[1, ["job_title", "city", "company_size", "industry"]] = sample.loc[
        0, ["job_title", "city", "company_size", "industry"]
    ]
    sample.loc[1, "required_skills"] = "|".join(
        reversed(sample.loc[0, "required_skills"].split("|"))
    )
    sample.loc[2, "country"] = sample.loc[0, "country"].lower()

    checks = explore.duplicate_checks(sample)

    assert checks["same_post"] == 1
    assert checks["label_variants"] == 1


def test_type_conversions(sample):
    conversions = {column: target for column, _, target in explore.type_conversions(sample)}
    assert conversions["annual_salary_usd"] == "entier"
    assert conversions["is_llm_role"] == "booléen"
    assert "benefits_score_10" not in conversions  # vraies décimales


def test_real_dataset_has_no_anomaly():
    df, raw = explore.load(explore.DEFAULT_CSV)
    assert df.shape == (1500, 25)
    assert not any(
        explore.missing_checks(df, raw, explore.count_malformed_lines(explore.DEFAULT_CSV)).values()
    )
    assert not any(explore.duplicate_checks(df).values())
    assert all(explore.range_checks(df).values())


def test_report_is_reproducible():
    assert explore.build_report(explore.DEFAULT_CSV) == explore.build_report(explore.DEFAULT_CSV)


def test_committed_report_is_up_to_date():
    """Le rapport versionné doit correspondre au CSV : sinon relancer le script."""
    assert explore.DEFAULT_REPORT.read_text(encoding="utf-8") == explore.build_report(
        explore.DEFAULT_CSV
    )
