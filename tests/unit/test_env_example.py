"""Vérifie que .env.example documente toutes les variables attendues."""

from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
REQUIRED = {
    "MYSQL_DATABASE",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_ROOT_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "APP_PORT",
}


def read_env(path: Path) -> dict[str, str]:
    pairs = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            pairs[key] = value
    return pairs


def test_all_variables_present():
    missing = REQUIRED - read_env(ENV_EXAMPLE).keys()
    assert not missing, f"Variables manquantes : {missing}"


def test_passwords_are_placeholders():
    env = read_env(ENV_EXAMPLE)
    for key in ("MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"):
        assert env[key].startswith("change-me"), f"{key} doit rester une valeur factice"
