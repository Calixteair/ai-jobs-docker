-- =============================================================================
-- 02_import.sql — Chargement des données nettoyées
-- Les CSV sont produits par scripts/cleaning.py lors du build de l'image
-- (database/Dockerfile) et copiés dans /var/lib/mysql-files, seul dossier
-- autorisé par l'option secure_file_priv de l'image officielle.
-- L'ordre des colonnes listées suit l'en-tête de chaque CSV.
-- =============================================================================

LOAD DATA INFILE '/var/lib/mysql-files/jobs.csv'
    INTO TABLE jobs
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\n'
    IGNORE 1 LINES
    (job_id, job_title, job_category, experience_level, years_of_experience,
     education_required, annual_salary_usd, salary_min_usd, salary_max_usd,
     city, country, remote_work, company_size, industry, ai_salary_premium_pct,
     demand_score, demand_growth_yoy_pct, benefits_score_10, posting_year,
     posting_month, is_senior, is_remote_friendly, is_llm_role, salary_tier,
     experience_rank, posting_period, salary_above_range);

LOAD DATA INFILE '/var/lib/mysql-files/skills.csv'
    INTO TABLE skills
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\n'
    IGNORE 1 LINES
    (skill_id, name);

LOAD DATA INFILE '/var/lib/mysql-files/job_skills.csv'
    INTO TABLE job_skills
    CHARACTER SET utf8mb4
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\n'
    IGNORE 1 LINES
    (job_id, skill_id);
