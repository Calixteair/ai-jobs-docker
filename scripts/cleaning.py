"""Nettoyage et préparation du dataset AI Jobs Market pour l'import MySQL.

Applique les décisions de docs/data/decisions_nettoyage.md (D1 à D10) et produit
trois fichiers CSV prêts à charger, un par table :

    jobs.csv        une ligne par offre (sans la colonne required_skills)
    skills.csv      une ligne par compétence distincte
    job_skills.csv  table de liaison offre <-> compétence

ainsi qu'un journal des transformations (journal_nettoyage.md).

Usage : python scripts/cleaning.py [chemin_csv] [dossier_sortie]
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "ai_jobs_market_2025_2026.csv"
DEFAULT_OUT = ROOT / "data" / "processed"

SKILL_SEPARATOR = "|"

DOMAINS = {
    "job_category": {
        "AI Engineering", "Architecture", "Business", "Data Engineering", "Data Science",
        "Governance", "Infrastructure", "ML Operations", "Product", "Research", "Robotics",
        "Security",
    },
    "experience_level": {"Entry (0-2 yrs)", "Mid (3-5 yrs)", "Senior (6-9 yrs)", "Lead (10+ yrs)"},
    "education_required": {
        "Associate's", "Bachelor's", "Bootcamp/Self-taught", "Master's", "PhD",
    },
    "remote_work": {"On-site", "Hybrid", "Fully Remote"},
    "company_size": {
        "Startup (1-50)", "SME (51-500)", "Mid-size (501-5000)", "Enterprise (5000+)",
        "Big Tech (FAANG+)",
    },
    "industry": {
        "Automotive", "Consulting", "Education", "Energy", "Finance", "Government",
        "Healthcare", "Manufacturing", "Media", "Research", "Retail", "Technology",
    },
    "salary_tier": {
        "Entry (<$100k)", "Mid ($100-150k)", "Upper-Mid ($150-200k)", "Senior ($200-300k)",
        "Elite (>$300k)",
    },
}  # fmt: skip

EXPERIENCE_RANK = {
    "Entry (0-2 yrs)": 1,
    "Mid (3-5 yrs)": 2,
    "Senior (6-9 yrs)": 3,
    "Lead (10+ yrs)": 4,
}

BOOL_COLUMNS = ["is_senior", "is_remote_friendly", "is_llm_role"]


@dataclass
class Journal:
    """Trace de chaque transformation : étape, lignes concernées, détail."""

    entries: list[tuple[str, int, str]] = field(default_factory=list)

    def add(self, step: str, rows: int, detail: str) -> None:
        self.entries.append((step, rows, detail))

    def to_markdown(self) -> str:
        lines = ["| Étape | Lignes concernées | Détail |", "|---|---|---|"]
        lines += [f"| {step} | {rows} | {detail} |" for step, rows, detail in self.entries]
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Garde-fous (D8)
# --------------------------------------------------------------------------- #


def check_integrity(df: pd.DataFrame) -> None:
    """Lève une ValueError si le dataset présente une anomalie bloquante."""
    missing = int(df.isna().sum().sum())
    if missing:
        raise ValueError(f"{missing} valeur(s) manquante(s) dans le dataset")
    duplicated_ids = df.loc[df["job_id"].duplicated(), "job_id"].tolist()
    if duplicated_ids:
        raise ValueError(f"job_id en double : {duplicated_ids[:5]}")
    for column, allowed in DOMAINS.items():
        unknown = set(df[column].unique()) - allowed
        if unknown:
            raise ValueError(f"Valeurs inattendues dans {column} : {sorted(unknown)}")


# --------------------------------------------------------------------------- #
# Transformations unitaires
# --------------------------------------------------------------------------- #


def parse_skills(raw: str) -> list[str]:
    """Découpe la chaîne de compétences, retire les espaces et les doublons (D1).

    L'ordre de première apparition est conservé.
    """
    skills = [skill.strip() for skill in raw.split(SKILL_SEPARATOR)]
    return list(dict.fromkeys(skill for skill in skills if skill))


def strip_text_columns(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Retire les espaces en début/fin de toutes les colonnes texte."""
    out = df.copy()
    text_columns = out.select_dtypes(include="object").columns
    changed = 0
    for column in text_columns:
        stripped = out[column].str.strip()
        changed += int((stripped != out[column]).sum())
        out[column] = stripped
    journal.add("Suppression des espaces parasites", changed, f"{len(text_columns)} colonnes texte")
    return out


def convert_types(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Salaire en entier (D5) et indicateurs 0/1 en booléens (D6)."""
    out = df.copy()
    if not (out["annual_salary_usd"] % 1 == 0).all():
        raise ValueError("annual_salary_usd contient des valeurs non entières")
    out["annual_salary_usd"] = out["annual_salary_usd"].astype(int)
    journal.add("Salaire annuel en entier", len(out), "float64 → int")
    for column in BOOL_COLUMNS:
        if not out[column].isin([0, 1]).all():
            raise ValueError(f"{column} contient des valeurs autres que 0/1")
        out[column] = out[column].astype(bool)
    journal.add("Indicateurs en booléens", len(out), ", ".join(BOOL_COLUMNS))
    return out


def add_derived_columns(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Ajoute experience_rank (D7), posting_period (D4) et salary_above_range (D2)."""
    out = df.copy()
    out["experience_rank"] = out["experience_level"].map(EXPERIENCE_RANK)
    out["posting_period"] = (
        out["posting_year"].astype(str) + "-" + out["posting_month"].astype(str).str.zfill(2)
    )
    out["salary_above_range"] = out["annual_salary_usd"] > out["salary_max_usd"]
    journal.add("Ajout de experience_rank", len(out), "Entry=1 … Lead=4")
    journal.add("Ajout de posting_period", len(out), "format AAAA-MM")
    journal.add(
        "Ajout de salary_above_range",
        int(out["salary_above_range"].sum()),
        "salaire au-dessus de la fourchette de référence du métier (conservé)",
    )
    return out


def deduplicate_skills(df: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Remplace required_skills par une liste propre et dédoublonnée (D1)."""
    out = df.copy()
    raw_counts = out["required_skills"].str.split(SKILL_SEPARATOR).str.len()
    out["required_skills"] = out["required_skills"].map(parse_skills)
    affected = int((out["required_skills"].str.len() != raw_counts).sum())
    journal.add("Dédoublonnage des compétences", affected, "ordre de première apparition conservé")
    return out


# --------------------------------------------------------------------------- #
# Normalisation (D9)
# --------------------------------------------------------------------------- #


def build_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Sépare le DataFrame nettoyé en tables jobs, skills et job_skills."""
    links = df[["job_id", "required_skills"]].explode("required_skills")
    links = links.rename(columns={"required_skills": "name"})

    skills = pd.DataFrame({"name": sorted(links["name"].unique())})
    skills.insert(0, "skill_id", range(1, len(skills) + 1))

    job_skills = links.merge(skills, on="name")[["job_id", "skill_id"]]
    job_skills = job_skills.sort_values(["job_id", "skill_id"]).reset_index(drop=True)
    jobs = df.drop(columns="required_skills")
    return jobs, skills, job_skills


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def clean(raw: pd.DataFrame, journal: Journal) -> pd.DataFrame:
    """Enchaîne les contrôles et transformations sur le dataset brut."""
    check_integrity(raw)
    journal.add("Contrôles d'intégrité", len(raw), "manquants, doublons de job_id, domaines")
    df = strip_text_columns(raw, journal)
    df = convert_types(df, journal)
    df = add_derived_columns(df, journal)
    return deduplicate_skills(df, journal)


def write_outputs(tables: dict[str, pd.DataFrame], journal: Journal, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        # Booléens en 0/1 : format directement compris par LOAD DATA de MySQL
        bool_columns = table.select_dtypes(include="bool").columns
        table.astype(dict.fromkeys(bool_columns, int)).to_csv(out_dir / f"{name}.csv", index=False)
    summary = "\n".join(f"- `{name}.csv` : {len(t)} lignes" for name, t in tables.items())
    (out_dir / "journal_nettoyage.md").write_text(
        f"# Journal de nettoyage\n\n{journal.to_markdown()}\n\n## Fichiers produits\n\n{summary}\n"
    )


def run(source: Path, out_dir: Path) -> dict[str, pd.DataFrame]:
    journal = Journal()
    cleaned = clean(pd.read_csv(source), journal)
    jobs, skills, job_skills = build_tables(cleaned)
    tables = {"jobs": jobs, "skills": skills, "job_skills": job_skills}
    write_outputs(tables, journal, out_dir)
    return tables


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    tables = run(source, out_dir)
    for name, table in tables.items():
        print(f"{name:<11} {len(table):>5} lignes")
    print(f"Fichiers écrits dans {out_dir}")


if __name__ == "__main__":
    main()
