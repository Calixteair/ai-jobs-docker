"""Profil du dataset AI Jobs Market (Phase 1 du sujet).

Génère docs/data/profil_dataset.md à partir du CSV brut. Le fichier est
entièrement reproductible : relancer le script après toute modification.

Usage : python scripts/explore.py [chemin_csv] [chemin_sortie]
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "ai_jobs_market_2025_2026.csv"
DEFAULT_OUT = ROOT / "docs" / "data" / "profil_dataset.md"

CATEGORICAL = [
    "job_category",
    "experience_level",
    "education_required",
    "remote_work",
    "company_size",
    "industry",
    "salary_tier",
    "country",
]


def md_table(df: pd.DataFrame) -> str:
    """Convertit un DataFrame en tableau Markdown (sans dépendance externe)."""
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = [
        "| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([header, sep, *rows])


def section_overview(df: pd.DataFrame) -> str:
    cols = pd.DataFrame(
        {
            "colonne": df.columns,
            "type pandas": [str(t) for t in df.dtypes],
            "valeurs distinctes": [df[c].nunique() for c in df.columns],
            "manquants": [int(df[c].isna().sum()) for c in df.columns],
            "exemple": [df[c].iloc[0] for c in df.columns],
        }
    )
    return (
        f"## 1. Dimensions et colonnes\n\n"
        f"- **{len(df)} lignes**, **{df.shape[1]} colonnes**\n"
        f"- Valeurs manquantes au total : **{int(df.isna().sum().sum())}**\n\n"
        f"{md_table(cols)}\n"
    )


def section_duplicates(df: pd.DataFrame) -> str:
    dup_ids = int(df["job_id"].duplicated().sum())
    dup_rows = int(df.drop(columns="job_id").duplicated().sum())
    id_format_ok = bool(df["job_id"].str.fullmatch(r"AIJOB\d{4}").all())
    return (
        "## 2. Doublons et identifiants\n\n"
        f"- Doublons de `job_id` : **{dup_ids}**\n"
        f"- Lignes identiques hors `job_id` : **{dup_rows}**\n"
        f"- Format `AIJOB` + 4 chiffres respecté partout : **{'oui' if id_format_ok else 'non'}**\n"
    )


def section_numeric(df: pd.DataFrame) -> str:
    desc = df.describe().T[["min", "mean", "50%", "max"]].round(2)
    desc.insert(0, "colonne", desc.index)
    desc = desc.rename(columns={"mean": "moyenne", "50%": "médiane"})
    return f"## 3. Variables numériques\n\n{md_table(desc)}\n"


def section_categorical(df: pd.DataFrame) -> str:
    parts = ["## 4. Variables catégorielles\n"]
    for col in CATEGORICAL:
        counts = df[col].value_counts().rename_axis(col).reset_index(name="offres")
        parts.append(f"### `{col}` ({len(counts)} valeurs)\n\n{md_table(counts)}\n")
    return "\n".join(parts)


def section_skills(df: pd.DataFrame) -> str:
    lists = df["required_skills"].str.split("|")
    exploded = lists.explode()
    stripped = exploded.str.strip()
    variants = stripped.groupby(stripped.str.lower()).nunique()
    rows_with_dup = lists.apply(lambda skills: len(skills) != len(set(skills)))
    sizes = lists.str.len()
    top = stripped.value_counts().head(15).rename_axis("compétence").reset_index(name="offres")
    examples = df.loc[rows_with_dup, ["job_id", "required_skills"]].head(5)
    return (
        "## 5. Compétences (`required_skills`)\n\n"
        "- Format : liste de compétences séparées par `|`\n"
        f"- Compétences par offre : min {sizes.min()}, "
        f"moyenne {sizes.mean():.1f}, max {sizes.max()}\n"
        f"- Compétences distinctes : **{stripped.nunique()}**\n"
        f"- Espaces parasites : **{int((exploded != stripped).sum())}**\n"
        f"- Variantes de casse (ex. `sql` / `SQL`) : **{int((variants > 1).sum())}**\n"
        f"- Offres contenant une compétence en double : **{int(rows_with_dup.sum())}**\n\n"
        f"Exemples de doublons :\n\n{md_table(examples)}\n\n"
        f"Top 15 :\n\n{md_table(top)}\n"
    )


def section_consistency(df: pd.DataFrame) -> str:
    out_of_range = df[
        (df["annual_salary_usd"] < df["salary_min_usd"])
        | (df["annual_salary_usd"] > df["salary_max_usd"])
    ]
    ranges_per_title = df.groupby("job_title")[["salary_min_usd", "salary_max_usd"]].nunique()
    one_range_per_title = bool((ranges_per_title == 1).all().all())
    above = int((out_of_range["annual_salary_usd"] > out_of_range["salary_max_usd"]).sum())
    out_by_level = (
        out_of_range["experience_level"].value_counts().rename_axis("experience_level")
    ).reset_index(name="offres hors fourchette")
    bins = pd.cut(
        df["years_of_experience"],
        [0, 2, 5, 9, 100],
        labels=["0-2", "3-5", "6-9", "10+"],
    )
    level_vs_years = pd.crosstab(df["experience_level"], bins)
    expected = {
        "Entry (0-2 yrs)": "0-2",
        "Mid (3-5 yrs)": "3-5",
        "Senior (6-9 yrs)": "6-9",
        "Lead (10+ yrs)": "10+",
    }
    coherent = sum(level_vs_years.loc[lvl, rng] for lvl, rng in expected.items())
    level_vs_years.insert(0, "experience_level", level_vs_years.index)

    senior_ok = (df["is_senior"] == df["experience_level"].str.match("Senior|Lead")).all()
    remote_ok = (df["is_remote_friendly"] == (df["remote_work"] != "On-site")).all()
    tier_bounds = df.groupby("salary_tier")["annual_salary_usd"].agg(["min", "max"]).reset_index()

    period = df["posting_year"].astype(str) + "-" + df["posting_month"].astype(str).str.zfill(2)
    by_period = period.value_counts().sort_index().rename_axis("période").reset_index(name="offres")
    share_2026 = (df["posting_year"] == 2026).mean() * 100

    return (
        "## 6. Contrôles de cohérence\n\n"
        "### 6.1 Salaire annuel vs fourchette min/max\n\n"
        f"- Offres dont `annual_salary_usd` sort de `[salary_min_usd, salary_max_usd]` : "
        f"**{len(out_of_range)}** ({len(out_of_range) / len(df):.1%})\n"
        f"- `salary_min_usd > salary_max_usd` : "
        f"**{int((df['salary_min_usd'] > df['salary_max_usd']).sum())}**\n"
        f"- Fourchette identique pour toutes les offres d'un même `job_title` : "
        f"**{'oui' if one_range_per_title else 'non'}** ({df['job_title'].nunique()} titres)\n"
        f"- Dont au-dessus du maximum : **{above}**, en dessous du minimum : "
        f"**{len(out_of_range) - above}**\n\n"
        f"{md_table(out_by_level)}\n\n"
        "### 6.2 Niveau d'expérience vs années d'expérience\n\n"
        f"{md_table(level_vs_years)}\n\n"
        f"Offres où les années correspondent au libellé du niveau : **{coherent}** "
        f"({coherent / len(df):.1%}).\n\n"
        "### 6.3 Colonnes dérivées\n\n"
        f"- `is_senior` = niveau Senior ou Lead : **{'cohérent' if senior_ok else 'incohérent'}**\n"
        f"- `is_remote_friendly` = Hybrid ou Fully Remote : "
        f"**{'cohérent' if remote_ok else 'incohérent'}**\n"
        "- Bornes réelles de `annual_salary_usd` par `salary_tier` :\n\n"
        f"{md_table(tier_bounds)}\n\n"
        "### 6.4 Répartition temporelle\n\n"
        f"Part des offres publiées en 2026 : **{share_2026:.1f} %** "
        "(3 mois sur 15 couverts).\n\n"
        f"{md_table(by_period)}\n"
    )


def build_report(df: pd.DataFrame, source: Path) -> str:
    sections = [
        section_overview(df),
        section_duplicates(df),
        section_numeric(df),
        section_categorical(df),
        section_skills(df),
        section_consistency(df),
    ]
    header = (
        "# Profil du dataset — AI Jobs Market 2025-2026\n\n"
        f"> Généré par `scripts/explore.py` à partir de `{source.relative_to(ROOT)}`. "
        "Ne pas éditer à la main.\n"
    )
    return "\n".join([header, *sections])


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    df = pd.read_csv(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report(df, source.resolve()))
    print(f"Profil écrit dans {output}")


if __name__ == "__main__":
    main()
