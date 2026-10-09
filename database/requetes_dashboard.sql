-- =============================================================================
-- Requêtes du dashboard
-- Version SQL brute, validée avant l'intégration dans app/queries.py.
-- Dans l'application, chaque requête reçoit en plus la clause WHERE des filtres
-- (pays, niveau, secteur, mode de travail, catégorie) en paramètres liés.
-- =============================================================================

-- Q1. KPI globaux : nombre d'offres, salaire moyen, score de demande moyen
SELECT COUNT(*)                         AS nb_offres,
       ROUND(AVG(annual_salary_usd))    AS salaire_moyen,
       ROUND(AVG(demand_score), 1)      AS demande_moyenne
FROM jobs;

-- Q2. KPI : salaire médian (MySQL n'a pas de fonction MEDIAN)
--     On numérote les salaires triés, puis on moyenne la ou les valeurs
--     centrales (une si le nombre d'offres est impair, deux s'il est pair).
WITH ordered AS (
    SELECT annual_salary_usd,
           ROW_NUMBER() OVER (ORDER BY annual_salary_usd) AS rn,
           COUNT(*)     OVER ()                            AS n
    FROM jobs
)
SELECT ROUND(AVG(annual_salary_usd)) AS salaire_median
FROM ordered
WHERE rn IN (FLOOR((n + 1) / 2), CEIL((n + 1) / 2));

-- Q3. Métiers les mieux payés (catégories)
SELECT job_category,
       COUNT(*)                       AS nb_offres,
       ROUND(AVG(annual_salary_usd))  AS salaire_moyen,
       MIN(annual_salary_usd)         AS salaire_min,
       MAX(annual_salary_usd)         AS salaire_max
FROM jobs
GROUP BY job_category
ORDER BY salaire_moyen DESC;

-- Q4. Rémunération et volume d'offres par pays
SELECT country,
       COUNT(*)                       AS nb_offres,
       ROUND(AVG(annual_salary_usd))  AS salaire_moyen
FROM jobs
GROUP BY country
ORDER BY nb_offres DESC;

-- Q5. Répartition On-site / Hybrid / Fully Remote
SELECT remote_work,
       COUNT(*)                                            AS nb_offres,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pourcentage
FROM jobs
GROUP BY remote_work
ORDER BY nb_offres DESC;

-- Q6. Compétences les plus demandées (jointure N-N)
SELECT s.name                AS competence,
       COUNT(*)              AS nb_offres
FROM job_skills js
JOIN skills s ON s.skill_id = js.skill_id
GROUP BY s.skill_id, s.name
ORDER BY nb_offres DESC
LIMIT 15;

-- Q7. Salaire selon le niveau d'expérience (ordre logique Entry → Lead)
SELECT experience_level,
       COUNT(*)                       AS nb_offres,
       ROUND(AVG(annual_salary_usd))  AS salaire_moyen
FROM jobs
GROUP BY experience_level, experience_rank
ORDER BY experience_rank;

-- Q8. Rôles LLM / GenAI vs autres : salaire, prime IA et demande
SELECT IF(is_llm_role, 'LLM / GenAI', 'Autres')  AS type_role,
       COUNT(*)                                   AS nb_offres,
       ROUND(AVG(annual_salary_usd))              AS salaire_moyen,
       ROUND(AVG(ai_salary_premium_pct), 1)       AS prime_ia_moyenne,
       ROUND(AVG(demand_score), 1)                AS demande_moyenne
FROM jobs
GROUP BY is_llm_role;

-- Q9. Secteurs : volume d'offres et rémunération
SELECT industry,
       COUNT(*)                       AS nb_offres,
       ROUND(AVG(annual_salary_usd))  AS salaire_moyen
FROM jobs
GROUP BY industry
ORDER BY salaire_moyen DESC;

-- Q10. Métiers avec les scores de demande les plus élevés
SELECT job_title,
       COUNT(*)                            AS nb_offres,
       ROUND(AVG(demand_score), 1)         AS demande_moyenne,
       ROUND(AVG(demand_growth_yoy_pct), 1) AS croissance_moyenne_pct
FROM jobs
GROUP BY job_title
ORDER BY demande_moyenne DESC
LIMIT 10;
