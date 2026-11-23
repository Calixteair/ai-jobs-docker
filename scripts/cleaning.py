"""Nettoyage du dataset AI Jobs Market pour l'import dans MySQL (issue #12).

Applique les décisions de docs/data/decisions_nettoyage.md (C1 à C7, K1 à K6) au
CSV brut et produit :

    data/processed/jobs.csv         une ligne par offre, sans la colonne required_skills
    data/processed/skills.csv       une ligne par compétence distincte
    data/processed/job_skills.csv   table de liaison offre <-> compétence
    docs/data/journal_nettoyage.md  trace de chaque transformation (avant / après)

Le script est idempotent : le relancer sur le même CSV produit exactement les
mêmes fichiers. Il s'arrête avec une erreur explicite si le CSV présente une
anomalie qu'il ne sait pas traiter (garde-fous C4 et K4).

Usage : python scripts/cleaning.py [chemin_csv] [dossier_sortie] [chemin_journal]
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "ai_jobs_market_2025_2026.csv"
DEFAULT_OUT = ROOT / "data" / "processed"
DEFAULT_JOURNAL = ROOT / "docs" / "data" / "journal_nettoyage.md"

SKILL_SEPARATOR = "|"
BOOL_COLUMNS = ["is_senior", "is_remote_friendly", "is_llm_role"]

EXPERIENCE_RANK = {
    "Entry (0-2 yrs)": 1,
    "Mid (3-5 yrs)": 2,
    "Senior (6-9 yrs)": 3,
    "Lead (10+ yrs)": 4,
}

# Bornes de salary_tier déduites des libellés (borne haute incluse)
SALARY_TIERS = {
    "Entry (<$100k)": (0, 100_000),
    "Mid ($100-150k)": (100_001, 150_000),
    "Upper-Mid ($150-200k)": (150_001, 200_000),
    "Senior ($200-300k)": (200_001, 300_000),
    "Elite (>$300k)": (300_001, 10**9),
}

# Colonnes à valeurs fermées : une valeur inconnue arrête le nettoyage
DOMAINS = {
    "experience_level": set(EXPERIENCE_RANK),
    "remote_work": {"On-site", "Hybrid", "Fully Remote"},
    "education_required": {
        "Bootcamp/Self-taught", "Associate's", "Bachelor's", "Master's", "PhD",
    },
    "company_size": {
        "Startup (1-50)", "SME (51-500)", "Mid-size (501-5000)", "Enterprise (5000+)",
        "Big Tech (FAANG+)",
    },
    "salary_tier": set(SALARY_TIERS),
}  # fmt: skip


class CleaningError(ValueError):
    """Le CSV présente une anomalie que le nettoyage refuse de corriger seul."""


@dataclass
class Step:
    name: str
    decision: str
    rows: int
    before: str = "—"
    after: str = "—"


@dataclass
class Journal:
    """Trace de chaque transformation, dans l'ordre où elle est appliquée."""

    steps: list[Step] = field(default_factory=list)

    def add(self, *args: object, **kwargs: object) -> None:
        self.steps.append(Step(*args, **kwargs))


# --------------------------------------------------------------------------- #
# Garde-fous
# --------------------------------------------------------------------------- #


def expected_salary_tier(salary: pd.Series) -> pd.Series:
    """Tranche attendue pour chaque salaire, d'après les bornes des libellés."""
    tiers = pd.Series("", index=salary.index)
    for tier, (low, high) in SALARY_TIERS.items():
        tiers[salary.between(low, high)] = tier
    return tiers


def skill_spelling_variants(skills: pd.Series) -> list[str]:
    """Compétences écrites de plusieurs façons (casse, espaces), ex. « SQL » et « sql »."""
    names = skills.str.split(SKILL_SEPARATOR, regex=False).explode().str.strip()
    names = names[names != ""]
    spellings = names.groupby(names.str.lower()).unique()
    return sorted(", ".join(sorted(v)) for v in spellings if len(v) > 1)


def integrity_problems(df: pd.DataFrame) -> list[str]:
    """Anomalies bloquantes : le nettoyage ne sait pas les corriger sans arbitrage."""
    problems = []
    missing = int(df.isna().sum().sum())
    if missing:
        problems.append(f"{missing} valeur(s) manquante(s)")
    duplicated = df.loc[df["job_id"].duplicated(), "job_id"].tolist()
    if duplicated:
        problems.append(f"job_id en double : {duplicated[:5]}")
    for column, allowed in DOMAINS.items():
        unknown = sorted(set(df[column].dropna().str.strip()) - allowed)
        if unknown:
            problems.append(f"valeur(s) inconnue(s) dans {column} : {unknown}")
    if missing or duplicated:
        return problems  # les règles suivantes supposent des données complètes
    level = df["experience_level"].str.strip()
    if not (df["is_senior"].astype(bool) == level.str.match("Senior|Lead")).all():
        problems.append("is_senior incohérent avec experience_level (K4)")
    remote = df["remote_work"].str.strip()
    if not (df["is_remote_friendly"].astype(bool) == (remote != "On-site")).all():
        problems.append("is_remote_friendly incohérent avec remote_work (K4)")
    tier = df["salary_tier"].str.strip()
    if not (expected_salary_tier(df["annual_salary_usd"]) == tier).all():
        problems.append("salary_tier incohérent avec annual_salary_usd (K4)")
    variants = skill_spelling_variants(df["required_skills"])
    if variants:
        problems.append(f"compétences écrites de plusieurs façons (C4) : {variants[:5]}")
    return problems


def check_integrity(df: pd.DataFrame, journal: Journal) -> None:
    problems = integrity_problems(df)
    if problems:
        raise CleaningError("Nettoyage interrompu : " + " ; ".join(problems))
    journal.add(
        "Contrôles d'intégrité",
        "C4, K4",
        len(df),
        after="manquants, doublons de job_id, domaines, colonnes dérivées, variantes : OK",
    )


# --------------------------------------------------------------------------- #
# Transformations
# --------------------------------------------------------------------------- #


def strip_text(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Retire les espaces en début et fin de toutes les colonnes texte."""
    out = df.copy()
    text_columns = out.select_dtypes(include="object").columns
    changed = pd.Series(False, index=out.index)
    for column in text_columns:
        stripped = out[column].str.strip()
        changed |= stripped != out[column]
        out[column] = stripped
    journal.add("Espaces en début et fin de texte retirés", "C4", int(changed.sum()))
    return out


def convert_types(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Salaire en entier et indicateurs 0/1 en booléens (rapport d'exploration §5)."""
    out = df.copy()
    salary = out["annual_salary_usd"]
    if not (salary % 1 == 0).all():
        raise CleaningError("annual_salary_usd contient des valeurs non entières")
    out["annual_salary_usd"] = salary.astype(int)
    journal.add(
        "Salaire annuel converti en entier",
        "exploration §5",
        len(out),
        before=f"`{salary.iloc[0]}` (décimal)",
        after=f"`{out['annual_salary_usd'].iloc[0]}` (entier)",
    )
    for column in BOOL_COLUMNS:
        if not out[column].isin([0, 1]).all():
            raise CleaningError(f"{column} contient des valeurs autres que 0 et 1")
        out[column] = out[column].astype(bool)
    journal.add(
        "Indicateurs convertis en booléens",
        "exploration §5",
        len(out),
        before="`0` / `1` (entier)",
        after=f"`False` / `True` ({', '.join(BOOL_COLUMNS)})",
    )
    return out


def parse_skills(raw: str) -> list[str]:
    """Découpe sur `|` uniquement (C1), retire les espaces et dédoublonne (C2).

    L'ordre de première apparition est conservé, ce qui rend la fonction
    idempotente : parse_skills("|".join(parse_skills(x))) == parse_skills(x).
    """
    skills = (skill.strip() for skill in raw.split(SKILL_SEPARATOR))
    return list(dict.fromkeys(skill for skill in skills if skill))


def clean_skills(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Remplace required_skills par une liste propre et dédoublonnée."""
    out = df.copy()
    raw = out["required_skills"]
    out["required_skills"] = raw.map(parse_skills)
    affected = (
        raw.str.split(SKILL_SEPARATOR, regex=False).str.len() != out["required_skills"].str.len()
    )
    example = affected.idxmax() if affected.any() else None
    journal.add(
        "Compétences découpées et dédoublonnées",
        "C1, C2",
        int(affected.sum()),
        before=f"`{out.loc[example, 'job_id']}` : `{raw[example]}`" if example is not None else "—",
        after=f"`{', '.join(out.loc[example, 'required_skills'])}`" if example is not None else "—",
    )
    return out


def add_derived_columns(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Ajoute experience_rank, posting_period (K5) et salary_above_range (K1)."""
    out = df.copy()
    out["experience_rank"] = out["experience_level"].map(EXPERIENCE_RANK)
    out["posting_period"] = (
        out["posting_year"].astype(str) + "-" + out["posting_month"].astype(str).str.zfill(2)
    )
    out["salary_above_range"] = out["annual_salary_usd"] > out["salary_max_usd"]
    journal.add(
        "Ajout de `experience_rank`",
        "tri Entry → Lead",
        len(out),
        after="Entry = 1, Mid = 2, Senior = 3, Lead = 4",
    )
    journal.add(
        "Ajout de `posting_period`",
        "K5",
        len(out),
        before="`posting_year` = 2026, `posting_month` = 3",
        after="`2026-03`",
    )
    journal.add(
        "Ajout de `salary_above_range` (salaires conservés)",
        "K1",
        int(out["salary_above_range"].sum()),
        after="`True` si `annual_salary_usd` > `salary_max_usd`",
    )
    return out


def build_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Éclate les compétences en tables skills et job_skills (C7)."""
    links = df[["job_id", "required_skills"]].explode("required_skills")
    links = links.rename(columns={"required_skills": "name"})
    skills = pd.DataFrame({"name": sorted(links["name"].unique())})
    skills.insert(0, "skill_id", range(1, len(skills) + 1))
    job_skills = (
        links.merge(skills, on="name")[["job_id", "skill_id"]]
        .sort_values(["job_id", "skill_id"])
        .reset_index(drop=True)
    )
    jobs = df.drop(columns="required_skills").sort_values("job_id").reset_index(drop=True)
    return {"jobs": jobs, "skills": skills, "job_skills": job_skills}


def table_problems(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Contraintes que la base imposera : clés primaires uniques, clés étrangères valides."""
    jobs, skills, links = tables["jobs"], tables["skills"], tables["job_skills"]
    problems = []
    if jobs["job_id"].duplicated().any():
        problems.append("jobs.job_id non unique")
    if skills["name"].duplicated().any() or skills["skill_id"].duplicated().any():
        problems.append("skills.skill_id ou skills.name non unique")
    if links.duplicated().any():
        problems.append("job_skills contient des couples en double")
    if not links["job_id"].isin(jobs["job_id"]).all():
        problems.append("job_skills référence une offre absente de jobs")
    if not links["skill_id"].isin(skills["skill_id"]).all():
        problems.append("job_skills référence une compétence absente de skills")
    if not jobs["job_id"].isin(links["job_id"]).all():
        problems.append("une offre n'a aucune compétence")
    return problems


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def clean(raw: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], Journal]:
    """Enchaîne contrôles et transformations ; renvoie les trois tables et le journal."""
    journal = Journal()
    check_integrity(raw, journal)
    df = strip_text(raw, journal)
    df = convert_types(df, journal)
    df = clean_skills(df, journal)
    df = add_derived_columns(df, journal)
    tables = build_tables(df)
    problems = table_problems(tables)
    if problems:
        raise CleaningError("Tables incohérentes : " + " ; ".join(problems))
    journal.add(
        "Éclatement en tables `jobs`, `skills`, `job_skills`",
        "C7",
        len(tables["job_skills"]),
        before="1 colonne `required_skills` par offre",
        after=f"{len(tables['skills'])} compétences, {len(tables['job_skills'])} couples",
    )
    return tables, journal


def to_csv_text(table: pd.DataFrame) -> str:
    """CSV prêt pour LOAD DATA : booléens en 0/1, fins de ligne Unix."""
    bool_columns = table.select_dtypes(include="bool").columns
    converted = table.astype(dict.fromkeys(bool_columns, int))
    return converted.to_csv(index=False, lineterminator="\n")


def render_journal(journal: Journal, tables: dict[str, pd.DataFrame], source: str) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|")

    lines = [
        "# Journal de nettoyage",
        "",
        f"> Généré par `scripts/cleaning.py` à partir de `{source}`. Ne pas éditer à la main.",
        ">",
        "> Décisions appliquées : [décisions de nettoyage](decisions_nettoyage.md).",
        "",
        "## Transformations",
        "",
        "| # | Étape | Décision | Lignes concernées | Avant | Après |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {i} | {cell(s.name)} | {s.decision} | {s.rows} | {cell(s.before)} | {cell(s.after)} |"
        for i, s in enumerate(journal.steps, start=1)
    ]
    lines += ["", "## Fichiers produits (`data/processed/`)", ""]
    lines += ["| Fichier | Lignes | Colonnes |", "|---|---|---|"]
    lines += [
        f"| `{name}.csv` | {len(table)} | {', '.join(f'`{c}`' for c in table.columns)} |"
        for name, table in tables.items()
    ]
    return "\n".join([*lines, ""])


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def run(source: Path, out_dir: Path, journal_path: Path) -> dict[str, pd.DataFrame]:
    tables, journal = clean(pd.read_csv(source))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        (out_dir / f"{name}.csv").write_text(to_csv_text(table), encoding="utf-8")
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(render_journal(journal, tables, display_path(source)), encoding="utf-8")
    return tables


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    journal_path = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_JOURNAL
    tables = run(source, out_dir, journal_path)
    for name, table in tables.items():
        print(f"{name:<11} {len(table):>5} lignes")
    print(f"Fichiers écrits dans {display_path(out_dir)}, journal : {display_path(journal_path)}")


if __name__ == "__main__":
    main()
