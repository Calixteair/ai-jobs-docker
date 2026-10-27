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


# --------------------------------------------------------------------------- #
# Compétences (issue #10)
# --------------------------------------------------------------------------- #


def test_split_skills_keeps_slash_inside_names():
    skills = pd.Series(["CI/CD|Cloud (AWS/GCP/Azure)|Python"])
    assert explore.split_skills(skills).iloc[0] == ["CI/CD", "Cloud (AWS/GCP/Azure)", "Python"]


def test_deduplicate_keeps_first_occurrence():
    assert explore.deduplicate(["SQL", "Python", "SQL", "Git"]) == ["SQL", "Python", "Git"]


def test_skill_format_checks_detect_each_anomaly():
    skills = pd.Series(["Python| SQL", "sql||Git", "Excel", "Python,R|Git"])
    checks = explore.skill_format_checks(skills)

    assert checks["single_item"] == 1  # « Excel »
    assert checks["other_separator"] == 1  # « Python,R »
    assert checks["padded"] == 1  # « SQL » précédé d'un espace
    assert checks["empty"] == 1  # « sql||Git »
    assert checks["case_variants"] == 1  # « SQL » et « sql »


def test_repetitions_are_counted_per_offer():
    skills = pd.Series(["SQL|Python|SQL", "Cloud|Git|Cloud|Git", "Python|Git"])

    stats = explore.repetition_stats(skills)
    repeated = explore.repeated_skills(skills)

    assert stats == {"offers": 2, "extra_mentions": 3, "max_repetition": 2, "several_repeated": 1}
    assert repeated.to_dict("records") == [
        {"compétence": "Cloud", "offres": 1},
        {"compétence": "Git", "offres": 1},
        {"compétence": "SQL", "offres": 1},
    ]


def test_skill_frequencies_count_offers_after_deduplication():
    skills = pd.Series(["SQL|Python|SQL", "SQL|Git"])
    table = explore.skill_frequencies(skills).set_index("compétence")

    assert table.loc["SQL", "offres"] == 2
    assert table.loc["SQL", "mentions brutes"] == 3
    assert table.loc["SQL", "% des offres"] == 100.0


def test_similar_skills_counts_offers_with_both_labels():
    skills = pd.Series(["Cloud|Cloud (AWS/GCP/Azure)", "Cloud|SQL", "Cloud (AWS/GCP/Azure)"])
    row = explore.similar_skills(skills, [("Cloud", "Cloud (AWS/GCP/Azure)")]).iloc[0]

    assert (row["offres avec A"], row["offres avec B"], row["offres avec les deux"]) == (2, 2, 1)


def test_real_dataset_skills_match_issue_10():
    """Critères d'acceptation de #10 : 93 compétences, 119 offres avec une répétition."""
    df, _ = explore.load(explore.DEFAULT_CSV)
    skills = df["required_skills"]

    assert len(explore.skill_frequencies(skills)) == 93
    assert explore.repetition_stats(skills)["offers"] == 119
    assert not any(explore.skill_format_checks(skills).values())
    assert explore.list_sizes(skills)["total"].tolist() == [9548, 9428]


# --------------------------------------------------------------------------- #
# Cohérence métier (issue #11)
# --------------------------------------------------------------------------- #


def test_salary_range_stats_detect_salaries_outside_the_range(sample):
    sample["salary_min_usd"], sample["salary_max_usd"] = 100_000, 200_000
    sample["annual_salary_usd"] = [90_000, 150_000, 240_000, 240_000, 210_000]

    stats = explore.salary_range_stats(sample)

    assert (stats["above"], stats["below"]) == (3, 1)
    assert (stats["max_ratio"], stats["at_max_ratio"]) == (1.2, 2)


def test_experience_consistency_counts_years_matching_the_level(sample):
    sample["experience_level"] = ["Entry (0-2 yrs)"] * 3 + ["Lead (10+ yrs)"] * 2
    sample["years_of_experience"] = [1, 2, 7, 12, 3]

    table, coherent = explore.experience_consistency(sample)

    assert coherent == 3  # 1 et 2 ans en Entry, 12 ans en Lead
    assert table.set_index("experience_level").loc["Entry (0-2 yrs)", "6-9"] == 1


def test_derived_checks_detect_an_inconsistent_column(sample):
    assert all(explore.derived_checks(sample).values())

    sample.loc[0, "is_remote_friendly"] = 1 - sample.loc[0, "is_remote_friendly"]
    sample.loc[1, "salary_tier"] = (
        "Elite (>$300k)" if sample.loc[1, "annual_salary_usd"] <= 300_000 else "Entry (<$100k)"
    )
    checks = explore.derived_checks(sample)

    assert not checks["is_remote_friendly"]
    assert not checks["salary_tier"]
    assert checks["is_senior"]


def test_real_dataset_matches_issue_11():
    """Critères d'acceptation de #11 : 288 salaires hors fourchette, colonnes dérivées OK."""
    df, _ = explore.load(explore.DEFAULT_CSV)

    assert explore.salary_range_stats(df)["above"] == 288
    assert explore.experience_consistency(df)[1] == 401
    assert all(explore.derived_checks(df).values())
    years = explore.time_distribution(df).set_index("année")
    assert years.loc[2026, "% des offres"] == 58.4
    assert explore.global_offers(df)["count"] == 82


def test_report_is_reproducible():
    assert explore.build_report(explore.DEFAULT_CSV) == explore.build_report(explore.DEFAULT_CSV)


def test_committed_report_is_up_to_date():
    """Le rapport versionné doit correspondre au CSV : sinon relancer le script."""
    assert explore.DEFAULT_REPORT.read_text(encoding="utf-8") == explore.build_report(
        explore.DEFAULT_CSV
    )
