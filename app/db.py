"""Connexion à MySQL : configuration depuis l'environnement, retry, erreurs lisibles.

Aucune dépendance à Streamlit : le module se teste seul et peut servir à d'autres
scripts. Les requêtes métier vivent dans queries.py ; ici, seulement la connexion.
"""

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Variables obligatoires, transmises au service app par compose.yaml
# (valeurs issues de MYSQL_DATABASE, MYSQL_USER et MYSQL_PASSWORD du .env)
REQUIRED_VARS = ("DB_NAME", "DB_USER", "DB_PASSWORD")


class DatabaseConfigError(Exception):
    """Une variable d'environnement nécessaire à la connexion est absente."""


class DatabaseUnavailable(Exception):
    """La base n'a pas répondu malgré les tentatives de connexion."""


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    connect_retries: int
    retry_delay_s: float

    @property
    def target(self) -> str:
        """Cible de connexion affichable : jamais le mot de passe."""
        return f"{self.user}@{self.host}:{self.port}/{self.database}"


def load_config(env: dict[str, str] | None = None) -> DbConfig:
    """Lit la configuration dans l'environnement (os.environ par défaut)."""
    env = os.environ if env is None else env
    missing = [name for name in REQUIRED_VARS if not env.get(name)]
    if missing:
        raise DatabaseConfigError(
            f"Variable(s) d'environnement manquante(s) : {', '.join(missing)}. "
            "Voir .env.example."
        )
    try:
        return DbConfig(
            # "db" = nom du service Compose, résolu par le DNS du réseau Docker
            host=env.get("DB_HOST", "db"),
            port=int(env.get("DB_PORT", "3306")),
            database=env["DB_NAME"],
            user=env["DB_USER"],
            password=env["DB_PASSWORD"],
            connect_retries=int(env.get("DB_CONNECT_RETRIES", "5")),
            retry_delay_s=float(env.get("DB_RETRY_DELAY", "2")),
        )
    except ValueError as exc:
        raise DatabaseConfigError(f"Valeur numérique invalide : {exc}") from exc


def build_url(config: DbConfig) -> URL:
    # URL.create échappe les caractères spéciaux du mot de passe (@, /, :…)
    return URL.create(
        "mysql+pymysql",
        username=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.database,
        query={"charset": "utf8mb4"},
    )


def create_db_engine(config: DbConfig) -> Engine:
    return create_engine(
        build_url(config),
        pool_pre_ping=True,  # détecte une connexion coupée (redémarrage de MySQL)
        pool_recycle=3600,
        connect_args={"connect_timeout": 5},
    )


def wait_for_db(
    engine: Engine,
    retries: int,
    delay_s: float,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Attend que la base réponde à SELECT 1, sinon lève DatabaseUnavailable.

    Filet de sécurité en plus du healthcheck Compose : l'app peut démarrer
    pendant un redémarrage de MySQL.
    """
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            # exc.orig = erreur du pilote, sans la requête ni les paramètres
            logger.warning(
                "Base injoignable (tentative %d/%d) : %s", attempt, retries, exc.orig or exc
            )
            if attempt < retries:
                sleep(delay_s)
        else:
            logger.info("Connexion à la base établie (tentative %d/%d)", attempt, retries)
            return
    raise DatabaseUnavailable(f"La base n'a pas répondu après {retries} tentative(s).")


def connect(env: dict[str, str] | None = None) -> tuple[Engine, DbConfig]:
    """Configuration + moteur + attente de la base : point d'entrée de l'app."""
    config = load_config(env)
    logger.info("Connexion à %s", config.target)
    engine = create_db_engine(config)
    wait_for_db(engine, config.connect_retries, config.retry_delay_s)
    return engine, config


def server_version(engine: Engine) -> str:
    """Version du serveur, lue par SQLAlchemy à la première connexion."""
    info = engine.dialect.server_version_info
    return ".".join(str(part) for part in info) if info else "inconnue"
