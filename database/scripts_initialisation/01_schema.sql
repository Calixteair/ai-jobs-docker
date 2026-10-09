-- =============================================================================
-- 01_schema.sql — Création des tables
-- Exécuté automatiquement par l'image mysql au premier démarrage (volume vide),
-- dans la base désignée par MYSQL_DATABASE.
-- Modèle détaillé : docs/BASE_DE_DONNEES.md
-- =============================================================================

CREATE TABLE jobs (
    job_id                 CHAR(9)            NOT NULL,
    job_title              VARCHAR(80)        NOT NULL,
    job_category           VARCHAR(40)        NOT NULL,
    experience_level       ENUM('Entry (0-2 yrs)', 'Mid (3-5 yrs)',
                                'Senior (6-9 yrs)', 'Lead (10+ yrs)') NOT NULL,
    experience_rank        TINYINT UNSIGNED   NOT NULL,
    years_of_experience    TINYINT UNSIGNED   NOT NULL,
    education_required     VARCHAR(30)        NOT NULL,
    annual_salary_usd      INT UNSIGNED       NOT NULL,
    salary_min_usd         INT UNSIGNED       NOT NULL,
    salary_max_usd         INT UNSIGNED       NOT NULL,
    salary_above_range     BOOLEAN            NOT NULL,
    salary_tier            VARCHAR(30)        NOT NULL,
    city                   VARCHAR(60)        NOT NULL,
    country                VARCHAR(40)        NOT NULL,
    remote_work            ENUM('On-site', 'Hybrid', 'Fully Remote') NOT NULL,
    company_size           VARCHAR(30)        NOT NULL,
    industry               VARCHAR(40)        NOT NULL,
    ai_salary_premium_pct  DECIMAL(4,1)       NOT NULL,
    demand_score           TINYINT UNSIGNED   NOT NULL,
    demand_growth_yoy_pct  DECIMAL(4,1)       NOT NULL,
    benefits_score_10      DECIMAL(3,1)       NOT NULL,
    posting_year           SMALLINT UNSIGNED  NOT NULL,
    posting_month          TINYINT UNSIGNED   NOT NULL,
    posting_period         CHAR(7)            NOT NULL,
    is_senior              BOOLEAN            NOT NULL,
    is_remote_friendly     BOOLEAN            NOT NULL,
    is_llm_role            BOOLEAN            NOT NULL,

    PRIMARY KEY (job_id),
    INDEX idx_jobs_country (country),
    INDEX idx_jobs_category (job_category),
    INDEX idx_jobs_title (job_title),
    INDEX idx_jobs_experience (experience_level),
    INDEX idx_jobs_industry (industry),
    INDEX idx_jobs_remote (remote_work),

    CONSTRAINT chk_jobs_salary_range CHECK (salary_min_usd <= salary_max_usd),
    CONSTRAINT chk_jobs_rank         CHECK (experience_rank BETWEEN 1 AND 4),
    CONSTRAINT chk_jobs_demand       CHECK (demand_score BETWEEN 0 AND 100),
    CONSTRAINT chk_jobs_benefits     CHECK (benefits_score_10 BETWEEN 0 AND 10),
    CONSTRAINT chk_jobs_month        CHECK (posting_month BETWEEN 1 AND 12)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE skills (
    skill_id  SMALLINT UNSIGNED  NOT NULL,
    name      VARCHAR(60)        NOT NULL,

    PRIMARY KEY (skill_id),
    UNIQUE KEY uq_skills_name (name)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE job_skills (
    job_id    CHAR(9)            NOT NULL,
    skill_id  SMALLINT UNSIGNED  NOT NULL,

    PRIMARY KEY (job_id, skill_id),
    INDEX idx_job_skills_skill (skill_id),
    CONSTRAINT fk_job_skills_job   FOREIGN KEY (job_id)   REFERENCES jobs (job_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_job_skills_skill FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
        ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;
