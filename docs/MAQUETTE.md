# Maquette du dashboard

> Base de discussion pour le Sprint 2. Chaque élément renvoie à une requête de [`database/requetes_dashboard.sql`](../database/requetes_dashboard.sql).

## Navigation

Application Streamlit multipage, filtres communs dans la barre latérale.

| Page | Contenu | Exigence du sujet |
|---|---|---|
| **Accueil** | Présentation du projet et du dataset, état de la connexion à la base | §7.1 page d'accueil, connexion |
| **Dashboard** | KPI + 5 visualisations, mis à jour par les filtres | §11.1, §11.3 |
| **Analyses** | 2 analyses originales + interprétation | §11.3 Initiative, §7.1 zone d'analyse |
| **Données** | Tableau des offres filtrées (consultation) | Confort, preuve que les données viennent de MySQL |

## Page Dashboard

```
┌──────────────┬─────────────────────────────────────────────────────────────────┐
│ FILTRES      │  AI Jobs Market 2025–2026                                       │
│              │                                                                 │
│ Pays      ▾  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│ Niveau    ▾  │  │ Offres     │ │ Salaire    │ │ Salaire    │ │ Demande    │    │
│ Secteur   ▾  │  │   1 500    │ │ moyen      │ │ médian     │ │ moyenne    │    │
│ Télétravail▾ │  │            │ │ 194 892 $  │ │ 180 000 $  │ │  87,5/100  │    │
│ Catégorie ▾  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│              │                                                                 │
│ [Réinitial.] │  ┌──────────────────────────────┐ ┌──────────────────────────┐  │
│              │  │ V1 Salaire moyen par         │ │ V2 Offres et salaire     │  │
│ ──────────── │  │    catégorie (barres horiz.) │ │    par pays (barres)     │  │
│ Connecté à   │  └──────────────────────────────┘ └──────────────────────────┘  │
│ MySQL ✔      │  ┌──────────────────────────────┐ ┌──────────────────────────┐  │
│ 1 500 offres │  │ V3 Répartition télétravail   │ │ V4 Top 15 compétences    │  │
│              │  │    (donut)                   │ │    (barres horiz.)       │  │
│              │  └──────────────────────────────┘ └──────────────────────────┘  │
│              │  ┌──────────────────────────────────────────────────────────┐   │
│              │  │ V5 Salaire selon le niveau d'expérience (box plot)       │   │
│              │  └──────────────────────────────────────────────────────────┘   │
│              │  ┌──────────────────────────────┐ ┌──────────────────────────┐  │
│              │  │ V6 LLM vs autres (barres     │ │ V7 Métiers les plus      │  │
│              │  │    groupées) — bonus         │ │    demandés — bonus      │  │
│              │  └──────────────────────────────┘ └──────────────────────────┘  │
└──────────────┴─────────────────────────────────────────────────────────────────┘
```

## Éléments

### KPI (sujet §11.1)

| KPI | Requête | Format |
|---|---|---|
| Nombre d'offres | Q1 | entier |
| Salaire annuel moyen | Q1 | `194 892 $` |
| Salaire annuel médian | Q2 | `180 000 $` |
| Score de demande moyen | Q1 | `87,5 / 100` |

### Filtres (sujet §11.2)

| Filtre | Colonne | Type de widget |
|---|---|---|
| Pays | `country` | multisélection (« Global » affiché à part) |
| Niveau d'expérience | `experience_level` | multisélection, triée par `experience_rank` |
| Secteur | `industry` | multisélection |
| Mode de travail | `remote_work` | multisélection |
| Catégorie de métier | `job_category` | multisélection |

Aucune sélection = pas de filtre. Valeurs chargées depuis la base, pas codées en dur.

### Visualisations (sujet §11.3)

| # | Question | Requête | Graphique |
|---|---|---|---|
| V1 | Quels métiers paient le plus ? | Q3 | barres horizontales triées |
| V2 | Comment la rémunération varie-t-elle selon le pays ? | Q4 | barres (volume) + points (salaire) |
| V3 | Quelle est la répartition On-site / Hybrid / Remote ? | Q5 | donut |
| V4 | Quelles compétences sont les plus demandées ? | Q6 | barres horizontales |
| V5 | Comment évolue le salaire selon l'expérience ? | Q7 | box plot (distribution, pas seulement la moyenne) |
| V6 | Les rôles LLM sont-ils mieux payés ou plus demandés ? | Q8 | barres groupées |
| V7 | Quels métiers ont la demande la plus forte ? | Q10 | barres horizontales |

## Page Analyses — pistes d'analyses originales

Format imposé par le sujet : question → indicateur → résultat → interprétation prudente.

1. **Le paradoxe de la prime IA** : les rôles LLM ont un salaire moyen plus élevé (207 746 $ contre 191 309 $) mais une prime IA moyenne plus faible (9,0 % contre 11,4 %). Pourquoi ? Piste : le salaire de base des rôles LLM est déjà élevé.
2. **Quelles compétences sont associées aux meilleurs salaires ?** Salaire moyen des offres requérant chaque compétence (au moins 50 offres pour être significatif), comparé à la moyenne générale.
3. *(alternative)* **Le télétravail est-il moins bien payé ?** Salaire moyen et médian par mode de travail, à niveau d'expérience égal.

Limites à rappeler sous chaque analyse : dataset pédagogique, sur-représentation du T1 2026, incohérences niveau/années (cf. `docs/data/decisions_nettoyage.md`).
