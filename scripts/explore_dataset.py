"""Exploration du dataset AI Jobs Market (issues #9 et #10, sujet Phase 1 points 1 à 5).

Contrôle les dimensions, les valeurs manquantes, les doublons, les types et le
format des compétences (`required_skills`) du CSV brut, puis écrit les résultats
chiffrés dans docs/data/exploration_dataset.md.

Le rapport est entièrement régénéré à chaque exécution : ne pas l'éditer à la main.
Le sens de chaque variable est décrit dans docs/data/dictionnaire_donnees.md et
les décisions qui en découlent dans docs/data/decisions_nettoyage.md.

Usage : python scripts/explore_dataset.py [chemin_csv] [chemin_rapport]
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "ai_jobs_market_2025_2026.csv"
DEFAULT_REPORT = ROOT / "docs" / "data" / "exploration_dataset.md"

EXPECTED_COLUMNS = 25
SKILL_SEPARATOR = "|"
JOB_ID_PATTERN = r"AIJOB\d{4}"

# Valeurs remplies qui signifient en réalité « pas de valeur »
DISGUISED_MISSING = {
    "na",
    "n/a",
    "nan",
    "null",
    "none",
    "unknown",
    "not specified",
    "-",
    "?",
    "tbd",
}

# Colonnes pour lesquelles une valeur nulle ou négative n'a pas de sens
STRICTLY_POSITIVE = [
    "annual_salary_usd", "salary_min_usd", "salary_max_usd", "demand_score", "benefits_score_10",
]  # fmt: skip

# Mesures chiffrées : deux offres peuvent différer uniquement par elles sans être distinctes
MEASURES = [
    "annual_salary_usd", "ai_salary_premium_pct", "demand_score", "demand_growth_yoy_pct",
    "benefits_score_10",
]  # fmt: skip

# Colonnes dont l'issue #9 demande de contrôler le type
NUMERIC_COLUMNS = [
    "annual_salary_usd", "salary_min_usd", "salary_max_usd", "years_of_experience",
    "demand_score", "benefits_score_10", "ai_salary_premium_pct", "demand_growth_yoy_pct",
    "posting_year", "posting_month", "is_senior", "is_remote_friendly", "is_llm_role",
]  # fmt: skip

MISSING_LABELS = {
    "nan": "Cellules `NaN` détectées par pandas",
    "blank": "Cellules vides ou ne contenant que des espaces",
    "disguised": "Valeurs déguisées (`n/a`, `unknown`, `-`, `?`…)",
    "non_positive": "Salaires ou scores nuls ou négatifs",
    "empty_skill": "Offres avec une compétence vide dans la liste",
    "malformed": f"Lignes du fichier qui n'ont pas {EXPECTED_COLUMNS} champs",
}

DUPLICATE_LABELS = {
    "job_id": "`job_id` en double",
    "job_id_format": "`job_id` hors du format `AIJOB` + 4 chiffres",
    "full_row": "Lignes identiques sur toutes les colonnes",
    "without_id": "Lignes identiques hors `job_id` (même offre sous deux identifiants)",
    "same_post": "Même poste, ville, entreprise, secteur et compétences",
    "without_measures": "Identiques hors `job_id`, compétences et mesures chiffrées",
    "label_variants": "Libellés écrits de plusieurs façons (casse, espaces)",
}

SKILL_FORMAT_LABELS = {
    "single_item": "Offres sans séparateur `|` (une seule compétence)",
    "other_separator": "Compétences contenant `,` ou `;` (autre séparateur possible)",
    "padded": "Compétences avec des espaces au début ou à la fin",
    "empty": "Compétences vides (`A||B`, `|` en fin de liste)",
    "case_variants": "Compétences écrites de plusieurs façons (casse, espaces)",
}

# Libellés proches repérés à la lecture des compétences : faut-il les fusionner ?
SIMILAR_SKILLS = [
    ("Cloud", "Cloud (AWS/GCP/Azure)"),
    ("Statistics", "Advanced Statistics"),
    ("Fine-tuning", "LLM Fine-tuning"),
    ("Prompt Engineering", "Prompt Design"),
    ("ML", "ML Algorithms"),
]


# --------------------------------------------------------------------------- #
# Chargement
# --------------------------------------------------------------------------- #


def load(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge le CSV deux fois : avec les types devinés par pandas, et en texte brut.

    La version brute ne convertit rien (ni types, ni « N/A » en NaN) : elle sert
    à voir les valeurs exactement telles qu'elles sont écrites dans le fichier.
    """
    typed = pd.read_csv(path)
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    return typed, raw


def count_malformed_lines(path: Path) -> int:
    """Nombre de lignes du fichier dont le nombre de champs est incorrect."""
    with path.open(newline="", encoding="utf-8") as file:
        return sum(len(row) != EXPECTED_COLUMNS for row in csv.reader(file))


def skill_set(skills: pd.Series) -> pd.Series:
    """Liste de compétences triée et sans répétition : l'ordre d'écriture ne compte plus."""
    return skills.str.split(SKILL_SEPARATOR).map(lambda s: SKILL_SEPARATOR.join(sorted(set(s))))


# --------------------------------------------------------------------------- #
# Contrôles
# --------------------------------------------------------------------------- #


def overview(df: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par colonne : type lu par pandas, nombre de valeurs distinctes, exemple."""
    return pd.DataFrame(
        {
            "colonne": df.columns,
            "type lu": [str(dtype) for dtype in df.dtypes],
            "valeurs distinctes": [df[column].nunique() for column in df.columns],
            "exemple": [df[column].iloc[0] for column in df.columns],
        }
    )


def missing_checks(df: pd.DataFrame, raw: pd.DataFrame, malformed_lines: int) -> dict[str, int]:
    """Valeurs manquantes réelles et déguisées."""
    stripped = raw.apply(lambda column: column.str.strip())
    skills = df["required_skills"].fillna("").str.split(SKILL_SEPARATOR)
    return {
        "nan": int(df.isna().sum().sum()),
        "blank": int(stripped.eq("").sum().sum()),
        "disguised": int(
            stripped.apply(lambda c: c.str.lower().isin(DISGUISED_MISSING)).sum().sum()
        ),
        "non_positive": int((df[STRICTLY_POSITIVE] <= 0).sum().sum()),
        "empty_skill": int(skills.map(lambda s: any(not skill.strip() for skill in s)).sum()),
        "malformed": malformed_lines,
    }


def duplicate_checks(df: pd.DataFrame) -> dict[str, int]:
    """Doublons d'offres, du plus évident (même identifiant) au plus caché."""
    with_skills = df.assign(skills_set=skill_set(df["required_skills"]))
    same_post = ["job_title", "city", "company_size", "industry", "skills_set"]
    descriptive = df.columns.drop(["job_id", "required_skills", *MEASURES])
    labels = df.select_dtypes("object").columns.drop(["job_id", "required_skills"])
    return {
        "job_id": int(df["job_id"].duplicated().sum()),
        "job_id_format": int((~df["job_id"].str.fullmatch(JOB_ID_PATTERN)).sum()),
        "full_row": int(df.duplicated().sum()),
        "without_id": int(df.drop(columns="job_id").duplicated().sum()),
        "same_post": int(with_skills.duplicated(same_post).sum()),
        "without_measures": int(df.duplicated(list(descriptive)).sum()),
        "label_variants": sum(
            df[column].nunique() - df[column].str.strip().str.lower().nunique() for column in labels
        ),
    }


def shared_skill_sets(df: pd.DataFrame) -> dict[str, int]:
    """Offres qui ont exactement la même liste de compétences qu'une autre offre."""
    skills = skill_set(df["required_skills"])
    shared = skills.duplicated(keep=False)
    titles_per_group = df[shared].groupby(skills[shared])["job_title"].nunique()
    return {
        "offers": int(shared.sum()),
        "groups": len(titles_per_group),
        "same_title_groups": int((titles_per_group == 1).sum()),
    }


def type_checks(df: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Type lu, texte non convertible, plage et nombre de décimales des colonnes chiffrées."""
    rows = []
    for column in NUMERIC_COLUMNS:
        values = df[column]
        rows.append(
            {
                "colonne": column,
                "type lu": str(values.dtype),
                "non numériques": int(pd.to_numeric(raw[column], errors="coerce").isna().sum()),
                # En texte : sinon pandas convertit toute la colonne en décimal
                "min": str(values.min()),
                "max": str(values.max()),
                "décimales écrites": int(raw[column].str.partition(".")[2].str.len().max()),
                "valeurs entières": "oui" if (values % 1 == 0).all() else "non",
            }
        )
    return pd.DataFrame(rows)


def range_checks(df: pd.DataFrame) -> dict[str, bool]:
    """Les valeurs sont-elles plausibles ?"""
    flags = ["is_senior", "is_remote_friendly", "is_llm_role"]
    return {
        "`posting_month` entre 1 et 12": bool(df["posting_month"].between(1, 12).all()),
        "`posting_year` égal à 2025 ou 2026": bool(df["posting_year"].isin([2025, 2026]).all()),
        "`demand_score` entre 0 et 100": bool(df["demand_score"].between(0, 100).all()),
        "`benefits_score_10` entre 0 et 10": bool(df["benefits_score_10"].between(0, 10).all()),
        "`years_of_experience` entre 0 et 50": bool(df["years_of_experience"].between(0, 50).all()),
        "`salary_min_usd` ≤ `salary_max_usd`": bool(
            (df["salary_min_usd"] <= df["salary_max_usd"]).all()
        ),
        "`is_senior`, `is_remote_friendly`, `is_llm_role` valent 0 ou 1": bool(
            df[flags].isin([0, 1]).all().all()
        ),
    }


def type_conversions(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Colonnes dont le type lu ne correspond pas aux valeurs : (colonne, actuel, cible)."""
    conversions = []
    for column in NUMERIC_COLUMNS:
        values = df[column]
        if values.dtype.kind == "f" and (values % 1 == 0).all():
            conversions.append((column, "décimal", "entier"))
        elif values.dtype.kind == "i" and values.isin([0, 1]).all():
            conversions.append((column, "entier 0/1", "booléen"))
    return conversions


# --------------------------------------------------------------------------- #
# Compétences (issue #10)
# --------------------------------------------------------------------------- #


def split_skills(skills: pd.Series) -> pd.Series:
    """Liste des compétences de chaque offre, telles qu'écrites (répétitions comprises)."""
    return skills.str.split(SKILL_SEPARATOR, regex=False)


def deduplicate(skills: list[str]) -> list[str]:
    """Règle retenue : chaque compétence une seule fois, à sa première position."""
    return list(dict.fromkeys(skills))


def skill_format_checks(skills: pd.Series) -> dict[str, int]:
    """Le format `A|B|C` est-il respecté partout ?"""
    items = split_skills(skills).explode()
    stripped = items.str.strip()
    named = stripped[stripped != ""]
    spellings = named.groupby(named.str.lower()).nunique()
    return {
        "single_item": int((~skills.str.contains(SKILL_SEPARATOR, regex=False)).sum()),
        "other_separator": int(items.str.contains(r"[,;]").sum()),
        "padded": int((items != stripped).sum()),
        "empty": int((stripped == "").sum()),
        "case_variants": int((spellings > 1).sum()),
    }


def list_sizes(skills: pd.Series) -> pd.DataFrame:
    """Nombre de compétences par offre, telles qu'écrites et après dédoublonnage."""
    raw_lists = split_skills(skills)
    sizes = {
        "telles qu'écrites": raw_lists.str.len(),
        "après dédoublonnage": raw_lists.map(deduplicate).str.len(),
    }
    return pd.DataFrame(
        [
            {
                "listes": name,
                "min": int(size.min()),
                "moyenne": round(float(size.mean()), 2),
                "max": int(size.max()),
                "total": int(size.sum()),
            }
            for name, size in sizes.items()
        ]
    )


def repetition_stats(skills: pd.Series) -> dict[str, int]:
    """Compétences écrites plusieurs fois dans une même offre."""
    counts = split_skills(skills).map(Counter)
    repeated_per_offer = counts.map(lambda c: sum(n > 1 for n in c.values()))
    return {
        "offers": int((repeated_per_offer > 0).sum()),
        "extra_mentions": int(counts.map(lambda c: sum(n - 1 for n in c.values())).sum()),
        "max_repetition": int(counts.map(lambda c: max(c.values())).max()),
        "several_repeated": int((repeated_per_offer > 1).sum()),
    }


def repeated_skills(skills: pd.Series) -> pd.DataFrame:
    """Pour chaque compétence répétée : nombre d'offres où elle apparaît plusieurs fois."""
    counts = split_skills(skills).map(Counter)
    repeated = counts.map(lambda c: [name for name, n in c.items() if n > 1]).explode().dropna()
    table = repeated.value_counts().rename_axis("compétence").reset_index(name="offres")
    return table.sort_values(["offres", "compétence"], ascending=[False, True], ignore_index=True)


def skill_frequencies(skills: pd.Series) -> pd.DataFrame:
    """Offres par compétence (après dédoublonnage) et mentions telles qu'écrites."""
    raw_lists = split_skills(skills)
    offers = raw_lists.map(deduplicate).explode().value_counts()
    mentions = raw_lists.explode().value_counts()
    table = pd.DataFrame(
        {
            "compétence": offers.index,
            "offres": offers.to_numpy(),
            "% des offres": (100 * offers / len(skills)).round(1).to_numpy(),
            "mentions brutes": mentions.reindex(offers.index).to_numpy(),
        }
    )
    return table.sort_values(["offres", "compétence"], ascending=[False, True], ignore_index=True)


def similar_skills(skills: pd.Series, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Pour chaque paire de libellés proches : offres avec l'un, l'autre, ou les deux."""
    items = split_skills(skills).explode()
    has = {name: items.eq(name).groupby(level=0).any() for pair in pairs for name in pair}
    return pd.DataFrame(
        [
            {
                "libellé A": first,
                "libellé B": second,
                "offres avec A": int(has[first].sum()),
                "offres avec B": int(has[second].sum()),
                "offres avec les deux": int((has[first] & has[second]).sum()),
            }
            for first, second in pairs
        ]
    )


# --------------------------------------------------------------------------- #
# Rapport Markdown
# --------------------------------------------------------------------------- #


def md_table(df: pd.DataFrame) -> str:
    """Tableau Markdown, sans dépendance supplémentaire (les `|` sont échappés)."""

    def cell(value: object) -> str:
        return str(value).replace("|", "\\|")

    header = "| " + " | ".join(cell(c) for c in df.columns) + " |"
    separator = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, separator, *rows])


def checks_table(results: dict[str, int], labels: dict[str, str]) -> str:
    """Tableau contrôle / résultat / statut : une anomalie = un résultat différent de 0."""
    table = pd.DataFrame(
        {
            "Contrôle": [labels[key] for key in results],
            "Résultat": list(results.values()),
            "Statut": ["✅" if count == 0 else "⚠️" for count in results.values()],
        }
    )
    return md_table(table)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def build_report(source: Path) -> str:
    df, raw = load(source)
    missing = missing_checks(df, raw, count_malformed_lines(source))
    duplicates = duplicate_checks(df)
    shared = shared_skill_sets(df)
    ranges = range_checks(df)
    conversions = type_conversions(df)

    period = df["posting_year"].astype(str) + "-" + df["posting_month"].astype(str).str.zfill(2)
    last_year = df["posting_year"].max()
    last_year_months = sorted(df.loc[df["posting_year"] == last_year, "posting_month"].unique())
    salary_written_as_float = int(raw["annual_salary_usd"].str.endswith(".0").sum())
    failed_ranges = [label for label, ok in ranges.items() if not ok]

    skills = df["required_skills"]
    skill_format = skill_format_checks(skills)
    sizes = list_sizes(skills)
    repetitions = repetition_stats(skills)
    repeated = repeated_skills(skills)
    frequencies = skill_frequencies(skills)
    overcounted = frequencies[frequencies["mentions brutes"] != frequencies["offres"]].assign(
        surcompte=lambda t: t["mentions brutes"] - t["offres"]
    )
    names = frequencies["compétence"]
    longest = names[names.str.len().idxmax()]
    non_ascii = sorted({char for name in names for char in name if not char.isascii()})
    with_slash = sorted(name for name in names if "/" in name)
    links = int(sizes.loc[sizes["listes"] == "après dédoublonnage", "total"].iloc[0])

    def count_anomalies(results: dict[str, int]) -> str:
        found = sum(1 for count in results.values() if count)
        return f"**{found} anomalie(s)** sur {len(results)} contrôles"

    conversions_table = pd.DataFrame(conversions, columns=["colonne", "type actuel", "type cible"])

    return "\n".join(
        [
            "# Exploration du dataset — AI Jobs Market 2025-2026",
            "",
            f"> Généré par `scripts/explore_dataset.py` à partir de `{display_path(source)}`. "
            "Ne pas éditer à la main : relancer le script.",
            ">",
            "> Sens et rôle de chaque variable : [dictionnaire des données]"
            "(dictionnaire_donnees.md).",
            "",
            "## Synthèse",
            "",
            f"- **{len(df)} lignes × {df.shape[1]} colonnes**",
            f"- Valeurs manquantes : {count_anomalies(missing)}",
            f"- Doublons d'offres : {count_anomalies(duplicates)}",
            f"- Plages de valeurs : **{len(failed_ranges)} anomalie(s)** "
            f"sur {len(ranges)} contrôles",
            f"- Types à convertir au nettoyage : **{len(conversions)} colonne(s)**",
            f"- Compétences : **{len(names)} distinctes**, format : "
            f"{count_anomalies(skill_format)}, **{repetitions['offers']} offres** avec une "
            "compétence répétée",
            "",
            "## 1. Dimensions et colonnes",
            "",
            md_table(overview(df)),
            "",
            "## 2. Valeurs manquantes",
            "",
            "Le CSV est relu en texte brut, sans conversion, pour repérer aussi les valeurs "
            "remplies mais vides de sens.",
            "",
            checks_table(missing, MISSING_LABELS),
            "",
            "## 3. Doublons",
            "",
            checks_table(duplicates, DUPLICATE_LABELS),
            "",
            f"**Faux positif écarté** : {shared['offers']} offres partagent exactement la même "
            f"liste de compétences avec au moins une autre offre ({shared['groups']} groupes). "
            f"Dans {shared['same_title_groups']} groupes sur {shared['groups']}, toutes les "
            "offres ont le même métier, et elles diffèrent par la ville, l'entreprise ou le "
            "salaire : ce sont des offres distinctes pour un même métier, pas des doublons.",
            "",
            "## 4. Types et plages de valeurs",
            "",
            md_table(type_checks(df, raw)),
            "",
            f"`annual_salary_usd` est lu en décimal car {salary_written_as_float} valeurs sur "
            f"{len(df)} sont écrites avec `.0` dans le fichier (ex. `239000.0`).",
            "",
            md_table(
                pd.DataFrame(
                    {
                        "Contrôle de plage": list(ranges),
                        "Statut": ["✅" if ok else "⚠️" for ok in ranges.values()],
                    }
                )
            ),
            "",
            f"Période couverte : de **{period.min()}** à **{period.max()}** "
            f"({period.nunique()} mois distincts). En {last_year}, seuls les mois "
            f"{', '.join(str(m) for m in last_year_months)} sont présents.",
            "",
            "## 5. Conversions de types à prévoir au nettoyage",
            "",
            md_table(conversions_table) if conversions else "Aucune.",
            "",
            "## 6. Compétences (`required_skills`)",
            "",
            "Chaque offre liste ses compétences dans une seule cellule, séparées par `|` "
            f"(ex. `{skills.iloc[0]}`). Le `/` n'est pas un séparateur : il fait partie du "
            f"nom de {len(with_slash)} compétence(s) ({', '.join(f'`{n}`' for n in with_slash)}).",
            "",
            checks_table(skill_format, SKILL_FORMAT_LABELS),
            "",
            "### 6.1 Taille des listes",
            "",
            md_table(sizes),
            "",
            f"**{len(names)} compétences distinctes.** Après éclatement, la table `skills` "
            f"comptera {len(names)} lignes et la table de liaison `job_skills` {links} lignes. "
            f"Nom le plus long : {len(longest)} caractères (`{longest}`) ; caractères non "
            f"ASCII : {', '.join(non_ascii) if non_ascii else 'aucun'}.",
            "",
            "### 6.2 Compétences répétées dans une même offre",
            "",
            f"- **{repetitions['offers']} offres** contiennent une compétence écrite plusieurs "
            f"fois ({repetitions['extra_mentions']} mentions en trop, au plus "
            f"×{repetitions['max_repetition']} ; {repetitions['several_repeated']} offre(s) "
            "avec plusieurs compétences répétées).",
            f"- Seules **{len(repeated)} compétences** sont concernées :",
            "",
            md_table(repeated),
            "",
            "Exemples :",
            "",
            md_table(
                df.loc[split_skills(skills).map(lambda s: len(s) != len(set(s))), ["job_id"]]
                .assign(required_skills=skills)
                .head(5)
            ),
            "",
            "Effet sur les comptages si l'on ne dédoublonne pas :",
            "",
            md_table(overcounted),
            "",
            "### 6.3 Libellés proches",
            "",
            "Paires repérées à la lecture de la liste. Une paire présente dans une même offre "
            "y est écrite comme deux compétences distinctes.",
            "",
            md_table(similar_skills(skills, SIMILAR_SKILLS)),
            "",
            "Décisions de traitement : [décisions de nettoyage](decisions_nettoyage.md).",
            "",
            f"## Annexe — fréquence des {len(names)} compétences",
            "",
            "`offres` : nombre d'offres qui demandent la compétence (après dédoublonnage) ; "
            "`mentions brutes` : nombre d'apparitions dans le CSV tel qu'il est écrit.",
            "",
            md_table(frequencies),
            "",
        ]
    )


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    report = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_REPORT
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(build_report(source), encoding="utf-8")
    print(f"Rapport écrit dans {display_path(report)}")


if __name__ == "__main__":
    main()
