"""Accès à la base MySQL : configuration, connexion avec nouvelles tentatives, requêtes.

Ce module ne dépend pas de Streamlit : il est testable seul et réutilisable
par les scripts et les tests d'intégration.
"""

import logging
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

REQUIRED_VARIABLES = ("DB_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")


class DatabaseUnavailable(RuntimeError):
    """La base est injoignable (conteneur arrêté, en cours de démarrage, réseau…)."""


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "DbConfig":
        """Lit la configuration dans les variables d'environnement (cf. .env.example)."""
        missing = [name for name in REQUIRED_VARIABLES if not env.get(name)]
        if missing:
            raise ValueError(f"Variables d'environnement manquantes : {', '.join(missing)}")
        return cls(
            host=env["DB_HOST"],
            port=int(env.get("DB_PORT", "3306")),
            user=env["MYSQL_USER"],
            password=env["MYSQL_PASSWORD"],
            database=env["MYSQL_DATABASE"],
        )

    def url(self) -> URL:
        # URL.create échappe le mot de passe : aucun souci avec les caractères spéciaux
        return URL.create(
            "mysql+pymysql",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            query={"charset": "utf8mb4"},
        )


def create_db_engine(config: DbConfig) -> Engine:
    # pool_pre_ping : vérifie la connexion avant usage (utile si MySQL a redémarré)
    return create_engine(config.url(), pool_pre_ping=True, pool_recycle=3600)


def wait_for_database(
    engine: Engine,
    attempts: int = 10,
    delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Attend que la base réponde, en réessayant `attempts` fois.

    Lève DatabaseUnavailable si la base ne répond toujours pas.
    """
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as error:
            logger.warning("Base injoignable (tentative %d/%d) : %s", attempt, attempts, error)
            if attempt < attempts:
                sleep(delay)
    raise DatabaseUnavailable(f"Base injoignable après {attempts} tentatives")


def fetch_dataframe(
    engine: Engine, sql: str, params: Mapping[str, object] | None = None
) -> pd.DataFrame:
    """Exécute une requête paramétrée et renvoie le résultat sous forme de DataFrame."""
    try:
        with engine.connect() as connection:
            return pd.read_sql(text(sql), connection, params=dict(params or {}))
    except OperationalError as error:
        raise DatabaseUnavailable("La base ne répond pas") from error
