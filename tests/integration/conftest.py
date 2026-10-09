"""Fixtures des tests d'intégration : connexion à la base démarrée par `make db-up`."""

import os
from pathlib import Path

import pytest

import cleaning
from db import DbConfig, create_db_engine, wait_for_database

ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            pairs[key] = value
    return pairs


@pytest.fixture(scope="session")
def engine():
    """Moteur vers le MySQL publié par compose.test.yaml (127.0.0.1:3307)."""
    env = {**load_dotenv(ROOT / ".env"), **os.environ}
    env["DB_HOST"] = os.environ.get("DB_TEST_HOST", "127.0.0.1")
    env["DB_PORT"] = os.environ.get("DB_TEST_PORT", "3307")
    engine = create_db_engine(DbConfig.from_env(env))
    wait_for_database(engine, attempts=5, delay=2.0)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def expected(tmp_path_factory):
    """Tables attendues, produites par le même script de nettoyage que l'image."""
    return cleaning.run(
        ROOT / "data" / "ai_jobs_market_2025_2026.csv", tmp_path_factory.mktemp("x")
    )
